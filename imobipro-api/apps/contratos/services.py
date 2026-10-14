"""Regras de contrato: numeração, ativação, comissão, reajuste e rescisão."""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.contratos.models import (
    PAPEIS_POR_TIPO,
    Comissao,
    ConfiguracaoComissao,
    Contrato,
    IndiceReajuste,
    PapelComissao,
    PapelParte,
    ParteContrato,
    Reajuste,
    StatusComissao,
    StatusContrato,
    TipoContrato,
)
from apps.core.auditoria import Acao, registrar, snapshot
from apps.core.money import dinheiro, percentual, ratear
from apps.imoveis.models import SituacaoImovel
from apps.imoveis.services import mudar_situacao

CAMPOS_AUDITADOS = ["status", "valor", "data_fim", "assinado_em"]


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 na API."""


@transaction.atomic
def gerar_numero(tenant, tipo) -> str:
    """Numeração sequencial por ano e tipo: LOC-2026-0001 / VEN-2026-0007."""

    prefixo = "LOC" if tipo == TipoContrato.LOCACAO else "VEN"
    ano = timezone.localdate().year

    ultimo = (
        Contrato.objects.select_for_update()
        .filter(tenant=tenant, numero__startswith=f"{prefixo}-{ano}-")
        .order_by("-numero")
        .first()
    )
    sequencia = int(ultimo.numero.split("-")[-1]) + 1 if ultimo else 1
    return f"{prefixo}-{ano}-{sequencia:04d}"


def configuracao_comissao(tenant) -> ConfiguracaoComissao:
    config, _ = ConfiguracaoComissao.objects.get_or_create(tenant=tenant)
    return config


# ------------------------------------------------------------------- criação


def criar_contrato(dados, tenant, partes=None, request=None):
    """Nasce sempre como rascunho: contrato só vale depois de assinado."""

    tipo = dados["tipo"]

    if tipo == TipoContrato.LOCACAO and not dados.get("data_fim"):
        raise RegraDeNegocio("Contrato de locação exige data de término.")

    with transaction.atomic():
        contrato = Contrato.objects.create(
            tenant=tenant,
            numero=gerar_numero(tenant, tipo),
            status=StatusContrato.RASCUNHO,
            **dados,
        )
        for parte in partes or []:
            adicionar_parte(
                contrato, parte["pessoa"], parte["papel"], parte.get("percentual", 100)
            )

    registrar(
        contrato, Acao.CRIACAO, request=request, depois=snapshot(contrato, CAMPOS_AUDITADOS)
    )
    return contrato


def adicionar_parte(contrato, pessoa, papel, percentual_parte=100):
    if papel not in PAPEIS_POR_TIPO[contrato.tipo]:
        validos = ", ".join(sorted(PAPEIS_POR_TIPO[contrato.tipo]))
        raise RegraDeNegocio(
            f"Papel {papel} não se aplica a contrato de "
            f"{contrato.get_tipo_display().lower()}. Válidos: {validos}."
        )

    if pessoa.tenant_id != contrato.tenant_id:
        raise RegraDeNegocio("Pessoa não pertence a esta imobiliária.")

    return ParteContrato.objects.create(
        contrato=contrato, pessoa=pessoa, papel=papel, percentual=percentual_parte
    )


def validar_para_ativacao(contrato):
    """Tudo que impede um contrato de entrar em vigor."""

    pendencias = []
    papeis = set(contrato.partes.values_list("papel", flat=True))

    if contrato.tipo == TipoContrato.LOCACAO:
        if PapelParte.LOCADOR not in papeis:
            pendencias.append("Contrato sem locador.")
        if PapelParte.LOCATARIO not in papeis:
            pendencias.append("Contrato sem locatário.")
        if not contrato.data_fim:
            pendencias.append("Contrato sem data de término.")
    else:
        if PapelParte.VENDEDOR not in papeis:
            pendencias.append("Contrato sem vendedor.")
        if PapelParte.COMPRADOR not in papeis:
            pendencias.append("Contrato sem comprador.")

    if not contrato.imovel.disponivel_para_negocio:
        pendencias.append(f"Imóvel está {contrato.imovel.get_situacao_display().lower()}.")

    if dinheiro(contrato.valor or 0) <= 0:
        pendencias.append("Valor do contrato não informado.")

    return pendencias


@transaction.atomic
def ativar_contrato(contrato, request=None, assinado_em=None):
    """Assinatura: tira o imóvel do mercado, gera comissões e as cobranças."""

    if contrato.status != StatusContrato.RASCUNHO:
        raise RegraDeNegocio("Só um rascunho pode ser ativado.")

    if pendencias := validar_para_ativacao(contrato):
        raise RegraDeNegocio(" ".join(pendencias))

    antes = snapshot(contrato, CAMPOS_AUDITADOS)
    contrato.status = StatusContrato.ATIVO
    contrato.assinado_em = assinado_em or timezone.localdate()
    contrato.save(update_fields=["status", "assinado_em", "atualizado_em"])

    nova_situacao = (
        SituacaoImovel.LOCADO
        if contrato.tipo == TipoContrato.LOCACAO
        else SituacaoImovel.VENDIDO
    )
    mudar_situacao(
        contrato.imovel,
        nova_situacao,
        request=request,
        motivo=f"contrato {contrato.numero}",
    )

    gerar_comissoes(contrato)

    if contrato.tipo == TipoContrato.LOCACAO:
        from apps.locacao.services import gerar_cobrancas_do_contrato

        gerar_cobrancas_do_contrato(contrato, meses=3)

    registrar(
        contrato,
        Acao.ALTERACAO,
        request=request,
        antes=antes,
        depois=snapshot(contrato, CAMPOS_AUDITADOS),
    )
    return contrato


# ----------------------------------------------------------------- comissões


def gerar_comissoes(contrato):
    """Congela percentual e valor no fechamento (handoff §1.7.4)."""

    if contrato.comissoes.exists():
        return list(contrato.comissoes.all())

    config = configuracao_comissao(contrato.tenant)

    if contrato.tipo == TipoContrato.VENDA:
        base = dinheiro(contrato.valor)
        total = percentual(base, config.percentual_venda)
        rateios = [
            (PapelComissao.CAPTADOR, config.rateio_captador, contrato.imovel.captador),
            (
                PapelComissao.VENDEDOR,
                config.rateio_vendedor,
                _vendedor_do_contrato(contrato),
            ),
            (PapelComissao.IMOBILIARIA, config.rateio_imobiliaria, None),
        ]
        partes = ratear(total, [peso for _, peso, _ in rateios])
    else:
        # Locação: a intermediação é o primeiro aluguel (ou o valor pactuado).
        base = dinheiro(contrato.taxa_intermediacao or contrato.valor)
        total = base
        rateios = [
            (PapelComissao.CAPTADOR, config.rateio_captador, contrato.imovel.captador),
            (PapelComissao.IMOBILIARIA, Decimal("100") - config.rateio_captador, None),
        ]
        partes = ratear(total, [peso for _, peso, _ in rateios])

    criadas = []
    for (papel, peso, usuario), valor in zip(rateios, partes, strict=True):
        criadas.append(
            Comissao.objects.create(
                tenant=contrato.tenant,
                contrato=contrato,
                usuario=usuario,
                papel=papel,
                percentual_snapshot=peso,
                base_calculo=base,
                valor=valor,
                status=StatusComissao.PREVISTA,
            )
        )

    return criadas


def _vendedor_do_contrato(contrato):
    """Quem fechou: o corretor do lead da proposta, se houver."""
    if contrato.proposta_id and contrato.proposta.lead.corretor_id:
        return contrato.proposta.lead.corretor
    return contrato.imovel.captador


def liberar_comissao(comissao, request=None):
    """Só libera com contrato ativo comissão de rascunho não existe."""

    if comissao.contrato.status != StatusContrato.ATIVO:
        raise RegraDeNegocio("Comissão só é liberada com contrato ativo.")
    if comissao.status != StatusComissao.PREVISTA:
        raise RegraDeNegocio("Esta comissão já foi liberada ou paga.")

    comissao.status = StatusComissao.LIBERADA
    comissao.liberada_em = timezone.localdate()
    comissao.save(update_fields=["status", "liberada_em"])
    registrar(
        comissao,
        Acao.ALTERACAO,
        request=request,
        antes={"status": "PREVISTA"},
        depois={"status": "LIBERADA"},
    )
    return comissao


def pagar_comissao(comissao, request=None):
    if comissao.status != StatusComissao.LIBERADA:
        raise RegraDeNegocio("Libere a comissão antes de registrar o pagamento.")

    comissao.status = StatusComissao.PAGA
    comissao.paga_em = timezone.localdate()
    comissao.save(update_fields=["status", "paga_em"])

    from apps.financeiro.services import lancar_despesa_de_comissao

    lancar_despesa_de_comissao(comissao, request=request)
    return comissao


# ------------------------------------------------------------------ reajuste


def previa_reajuste(contrato, percentual_indice):
    """Calcula sem gravar a tela mostra antes de o gestor confirmar."""

    if contrato.tipo != TipoContrato.LOCACAO:
        raise RegraDeNegocio("Só contrato de locação é reajustado.")
    if contrato.indice_reajuste == IndiceReajuste.SEM_REAJUSTE:
        raise RegraDeNegocio("Este contrato foi fechado sem reajuste.")

    anterior = dinheiro(contrato.valor)
    novo = dinheiro(anterior * (Decimal("1") + Decimal(str(percentual_indice)) / 100))
    return {
        "valor_anterior": anterior,
        "percentual": Decimal(str(percentual_indice)),
        "valor_novo": novo,
        "diferenca": dinheiro(novo - anterior),
        "indice": contrato.indice_reajuste,
    }


@transaction.atomic
def aplicar_reajuste(contrato, percentual_indice, request=None, data_aplicacao=None):
    previa = previa_reajuste(contrato, percentual_indice)

    if contrato.status != StatusContrato.ATIVO:
        raise RegraDeNegocio("Só contrato ativo é reajustado.")

    antes = snapshot(contrato, CAMPOS_AUDITADOS)
    contrato.valor = previa["valor_novo"]
    contrato.save(update_fields=["valor", "atualizado_em"])

    reajuste = Reajuste.objects.create(
        contrato=contrato,
        data_aplicacao=data_aplicacao or timezone.localdate(),
        indice=contrato.indice_reajuste,
        percentual=previa["percentual"],
        valor_anterior=previa["valor_anterior"],
        valor_novo=previa["valor_novo"],
    )

    registrar(
        contrato,
        Acao.ALTERACAO,
        request=request,
        antes=antes,
        depois=snapshot(contrato, CAMPOS_AUDITADOS),
    )

    from apps.accounts.models import Papel
    from apps.notificacoes.models import TipoNotificacao
    from apps.notificacoes.services import notificar_equipe

    notificar_equipe(
        contrato.tenant,
        [Papel.ADMIN, Papel.FINANCEIRO],
        tipo=TipoNotificacao.REAJUSTE_APLICADO,
        titulo=f"Reajuste aplicado em {contrato.numero}",
        descricao=(
            f"{previa['percentual']}% de R$ {previa['valor_anterior']} "
            f"para R$ {previa['valor_novo']}."
        ),
        dados={"contrato_id": str(contrato.pk)},
    )
    return reajuste


# ------------------------------------------------------------------ rescisão


def calcular_multa_rescisoria(contrato, data_rescisao=None):
    """Multa proporcional: multa_meses × meses_restantes / prazo_total.

    É a regra da Lei do Inquilinato (art. 4º): quem sai antes paga proporcional
    ao que falta, não a multa cheia.
    """

    if contrato.tipo != TipoContrato.LOCACAO or not contrato.data_fim:
        return dinheiro(0)

    data_rescisao = data_rescisao or timezone.localdate()

    if data_rescisao >= contrato.data_fim:
        return dinheiro(0)

    dias_restantes = (contrato.data_fim - data_rescisao).days
    dias_totais = (contrato.data_fim - contrato.data_inicio).days or 1
    multa_cheia = dinheiro(contrato.valor) * contrato.multa_rescisoria_meses

    return dinheiro(multa_cheia * Decimal(dias_restantes) / Decimal(dias_totais))


@transaction.atomic
def rescindir_contrato(contrato, motivo, request=None, data_rescisao=None):
    if contrato.status != StatusContrato.ATIVO:
        raise RegraDeNegocio("Só contrato ativo pode ser rescindido.")

    data_rescisao = data_rescisao or timezone.localdate()
    multa = calcular_multa_rescisoria(contrato, data_rescisao)

    antes = snapshot(contrato, CAMPOS_AUDITADOS)
    contrato.status = StatusContrato.RESCINDIDO
    contrato.rescindido_em = data_rescisao
    contrato.motivo_rescisao = motivo
    contrato.multa_rescisao_calculada = multa
    contrato.save(
        update_fields=[
            "status",
            "rescindido_em",
            "motivo_rescisao",
            "multa_rescisao_calculada",
            "atualizado_em",
        ]
    )

    # Imóvel volta ao mercado; cobranças futuras são canceladas.
    if contrato.tipo == TipoContrato.LOCACAO:
        mudar_situacao(
            contrato.imovel,
            SituacaoImovel.DISPONIVEL,
            request=request,
            motivo=f"rescisão do {contrato.numero}",
        )
        from apps.locacao.services import cancelar_cobrancas_futuras

        cancelar_cobrancas_futuras(contrato, a_partir_de=data_rescisao)

    contrato.comissoes.filter(status=StatusComissao.PREVISTA).update(
        status=StatusComissao.CANCELADA
    )

    registrar(
        contrato,
        Acao.ALTERACAO,
        request=request,
        antes=antes,
        depois=snapshot(contrato, CAMPOS_AUDITADOS),
    )
    return contrato


def encerrar_contrato(contrato, request=None):
    """Fim natural do prazo, sem multa."""

    if contrato.status != StatusContrato.ATIVO:
        raise RegraDeNegocio("Só contrato ativo pode ser encerrado.")

    contrato.status = StatusContrato.ENCERRADO
    contrato.save(update_fields=["status", "atualizado_em"])

    if contrato.tipo == TipoContrato.LOCACAO:
        mudar_situacao(
            contrato.imovel,
            SituacaoImovel.DISPONIVEL,
            request=request,
            motivo=f"término do {contrato.numero}",
        )
    return contrato


def contratos_a_vencer(tenant, dias=90):
    limite = timezone.localdate() + timedelta(days=dias)
    return Contrato.objects.filter(
        tenant=tenant,
        status=StatusContrato.ATIVO,
        data_fim__isnull=False,
        data_fim__lte=limite,
        data_fim__gte=timezone.localdate(),
    ).select_related("imovel")
