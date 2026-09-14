"""Geração de cobrança, baixa, repasse e régua de inadimplência."""

import re
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.auditoria import Acao, registrar, snapshot
from apps.core.money import dinheiro, percentual
from apps.locacao.models import (
    REGUA_DE_COBRANCA,
    Cobranca,
    EventoCobranca,
    Repasse,
    StatusCobranca,
    StatusRepasse,
)


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 na API."""


def primeiro_dia(referencia: date) -> date:
    return referencia.replace(day=1)


def somar_meses(referencia: date, meses: int) -> date:
    mes = referencia.month - 1 + meses
    ano = referencia.year + mes // 12
    return date(ano, mes % 12 + 1, 1)


def data_de_vencimento(competencia: date, dia: int) -> date:
    """Dia de vencimento limitado a 28 evita mês sem dia 29/30/31."""
    return competencia.replace(day=min(dia, 28))


def compor_valores(contrato):
    """Monta a cobrança do mês a partir do contrato e dos custos do imóvel."""

    imovel = contrato.imovel
    aluguel = dinheiro(contrato.valor)
    condominio = (
        dinheiro(imovel.valor_condominio or 0)
        if contrato.inclui_condominio
        else dinheiro(0)
    )
    iptu = dinheiro(imovel.valor_iptu_mensal or 0) if contrato.inclui_iptu else dinheiro(0)
    seguro = dinheiro(contrato.valor_seguro_incendio or 0)

    return {
        "valor_aluguel": aluguel,
        "valor_condominio": condominio,
        "valor_iptu": iptu,
        "valor_seguro": seguro,
        "outros": dinheiro(0),
        "valor_total": dinheiro(aluguel + condominio + iptu + seguro),
    }


@transaction.atomic
def nosso_numero(contrato, competencia):
    """Identificador do boleto, o mesmo que volta no arquivo de retorno.

    Cabe nas 11 posições que o CNAB 400 reserva: último dígito do ano do
    contrato + sequencial do contrato (4) + competência AAAAMM (6). Sem esse
    número, o retorno do banco não encontra cobrança nenhuma para baixar.
    """

    digitos = re.sub(r"\D", "", contrato.numero)
    ano, sequencial = digitos[:4], digitos[4:]
    return f"{ano[-1]}{sequencial.rjust(4, '0')[-4:]}{competencia:%Y%m}"


def gerar_cobranca(contrato, competencia):
    """Idempotente: chamar duas vezes para o mesmo mês não duplica cobrança."""

    competencia = primeiro_dia(competencia)

    existente = Cobranca.objects.filter(contrato=contrato, competencia=competencia).first()
    if existente:
        return existente

    valores = compor_valores(contrato)
    return Cobranca.objects.create(
        tenant=contrato.tenant,
        contrato=contrato,
        competencia=competencia,
        vencimento=data_de_vencimento(competencia, contrato.dia_vencimento),
        nosso_numero=nosso_numero(contrato, competencia),
        **valores,
    )


def gerar_cobrancas_do_contrato(contrato, meses=1, a_partir_de=None):
    """Gera as próximas N competências a partir do início da vigência."""

    inicio = primeiro_dia(a_partir_de or max(contrato.data_inicio, timezone.localdate()))
    geradas = []

    for indice in range(meses):
        competencia = somar_meses(inicio, indice)
        if contrato.data_fim and competencia > contrato.data_fim:
            break
        geradas.append(gerar_cobranca(contrato, competencia))

    return geradas


def cancelar_cobrancas_futuras(contrato, a_partir_de=None):
    """Rescisão não deixa cobrança em aberto para meses que não vão existir."""

    corte = a_partir_de or timezone.localdate()
    return Cobranca.objects.filter(
        contrato=contrato, status=StatusCobranca.ABERTA, vencimento__gt=corte
    ).update(status=StatusCobranca.CANCELADA)


# --------------------------------------------------------------- multa e juros


def calcular_encargos(cobranca, data_pagamento=None):
    """Multa fixa por atraso + juros de mora pro rata die (padrão de mercado)."""

    data_pagamento = data_pagamento or timezone.localdate()
    dias = (data_pagamento - cobranca.vencimento).days

    if dias <= 0:
        return {"multa": dinheiro(0), "juros": dinheiro(0), "dias_atraso": 0}

    contrato = cobranca.contrato
    base = dinheiro(cobranca.valor_total)
    multa = percentual(base, contrato.multa_atraso_percent)
    juros_dia = Decimal(str(contrato.juros_mora_mes_percent)) / Decimal("30")
    juros = percentual(base, juros_dia * dias)

    return {"multa": multa, "juros": juros, "dias_atraso": dias}


@transaction.atomic
def baixar_cobranca(cobranca, valor_pago, data_pagamento=None, forma="", request=None):
    """Registra o recebimento, calcula encargos e prepara o repasse."""

    if cobranca.status == StatusCobranca.PAGA:
        raise RegraDeNegocio("Esta cobrança já foi baixada.")
    if cobranca.status == StatusCobranca.CANCELADA:
        raise RegraDeNegocio("Cobrança cancelada não recebe baixa.")

    data_pagamento = data_pagamento or timezone.localdate()
    encargos = calcular_encargos(cobranca, data_pagamento)
    antes = snapshot(cobranca, ["status", "valor_pago", "valor_total"])

    cobranca.valor_multa = encargos["multa"]
    cobranca.valor_juros = encargos["juros"]
    cobranca.valor_total = dinheiro(
        cobranca.valor_aluguel
        + cobranca.valor_condominio
        + cobranca.valor_iptu
        + cobranca.valor_seguro
        + cobranca.outros
        + encargos["multa"]
        + encargos["juros"]
    )
    cobranca.valor_pago = dinheiro(valor_pago)
    cobranca.pago_em = data_pagamento
    cobranca.forma_pagamento = forma
    cobranca.status = StatusCobranca.PAGA
    cobranca.save()

    from apps.financeiro.services import lancar_receita_de_cobranca

    lancar_receita_de_cobranca(cobranca, request=request)
    repasse = gerar_repasse(cobranca)

    registrar(
        cobranca,
        Acao.ALTERACAO,
        request=request,
        antes=antes,
        depois=snapshot(cobranca, ["status", "valor_pago", "valor_total"]),
    )

    from apps.accounts.models import Papel
    from apps.notificacoes.models import TipoNotificacao
    from apps.notificacoes.services import notificar_equipe

    notificar_equipe(
        cobranca.tenant,
        [Papel.FINANCEIRO, Papel.ADMIN],
        tipo=TipoNotificacao.PAGAMENTO_RECEBIDO,
        titulo=f"Recebido R$ {cobranca.valor_pago}",
        descricao=f"{cobranca.contrato.numero} competência {cobranca.competencia:%m/%Y}.",
        dados={"cobranca_id": str(cobranca.pk), "repasse_id": str(repasse.pk)},
    )
    return cobranca


# ------------------------------------------------------------------ repasse


@transaction.atomic
def gerar_repasse(cobranca, retencoes=None):
    """Repasse = aluguel recebido − taxa de administração − retenções.

    Condomínio e IPTU não entram: são repasse a terceiro, não receita do dono.
    """

    if hasattr(cobranca, "repasse"):
        return cobranca.repasse

    contrato = cobranca.contrato
    bruto = dinheiro(cobranca.valor_aluguel)
    taxa = percentual(bruto, contrato.taxa_administracao_percent)
    retencoes = retencoes or []
    total_retido = dinheiro(sum(Decimal(str(item.get("valor", 0))) for item in retencoes))

    return Repasse.objects.create(
        tenant=contrato.tenant,
        contrato=contrato,
        cobranca=cobranca,
        competencia=cobranca.competencia,
        valor_bruto=bruto,
        taxa_administracao=taxa,
        retencoes=retencoes,
        valor_liquido=dinheiro(bruto - taxa - total_retido),
        status=StatusRepasse.PENDENTE,
    )


def liquidar_repasse(repasse, data_pagamento=None, request=None):
    if repasse.status == StatusRepasse.PAGO:
        raise RegraDeNegocio("Este repasse já foi pago.")
    if repasse.cobranca and repasse.cobranca.status != StatusCobranca.PAGA:
        raise RegraDeNegocio("Não se repassa aluguel que ainda não foi recebido.")

    antes = snapshot(repasse, ["status", "valor_liquido"])
    repasse.status = StatusRepasse.PAGO
    repasse.pago_em = data_pagamento or timezone.localdate()
    repasse.save(update_fields=["status", "pago_em"])

    from apps.financeiro.services import lancar_despesa_de_repasse

    lancar_despesa_de_repasse(repasse, request=request)

    registrar(
        repasse,
        Acao.ALTERACAO,
        request=request,
        antes=antes,
        depois=snapshot(repasse, ["status", "valor_liquido"]),
    )
    return repasse


def adicionar_retencao(repasse, descricao, valor):
    """Manutenção paga pela imobiliária sai do repasse do proprietário."""

    if repasse.status == StatusRepasse.PAGO:
        raise RegraDeNegocio("Repasse já pago não aceita retenção.")

    repasse.retencoes = [*repasse.retencoes, {"descricao": descricao, "valor": str(valor)}]
    repasse.valor_liquido = dinheiro(
        repasse.valor_bruto - repasse.taxa_administracao - repasse.total_retencoes
    )
    repasse.save(update_fields=["retencoes", "valor_liquido"])
    return repasse


# ------------------------------------------------------- régua de cobrança


def etapa_devida(cobranca):
    """Etapa mais avançada que já venceu e ainda não foi enviada.

    Se o sistema ficou fora do ar e a cobrança chegou a D+15 sem nenhum
    disparo, o inquilino recebe o aviso formal não o lembrete de D+1. Enviar
    o lembrete depois do aviso formal seria incoerente e enfraqueceria a
    cobrança.
    """

    dias = cobranca.dias_de_atraso
    enviadas = set(cobranca.etapas_cobranca_enviadas or [])

    vencidas = [etapa for gatilho, etapa in REGUA_DE_COBRANCA if dias >= gatilho]
    if not vencidas:
        return None

    mais_avancada = vencidas[-1]
    return None if mais_avancada in enviadas else mais_avancada


def executar_etapa_da_regua(cobranca, etapa):
    """Registra o disparo e envia o aviso ao inquilino."""

    from django.core.mail import send_mail

    locatario = cobranca.contrato.locatario
    destinatario = locatario.pessoa.email if locatario else ""

    EventoCobranca.objects.create(
        cobranca=cobranca,
        etapa=etapa,
        canal="EMAIL" if destinatario else "SEM_CANAL",
        destinatario=destinatario,
        detalhe=f"{cobranca.dias_de_atraso} dias de atraso.",
    )

    # Etapas anteriores à disparada são dadas por superadas: não voltam à fila.
    ordem = [etapa_da_regua for _, etapa_da_regua in REGUA_DE_COBRANCA]
    ate_aqui = ordem[: ordem.index(etapa) + 1]
    cobranca.etapas_cobranca_enviadas = sorted(
        set(cobranca.etapas_cobranca_enviadas or []) | set(ate_aqui), key=ordem.index
    )
    if cobranca.status == StatusCobranca.ABERTA:
        cobranca.status = StatusCobranca.ATRASADA
    cobranca.save(update_fields=["etapas_cobranca_enviadas", "status"])

    if destinatario:
        send_mail(
            f"Cobrança em aberto {cobranca.contrato.numero}",
            (
                f"Competência {cobranca.competencia:%m/%Y}, vencida em "
                f"{cobranca.vencimento:%d/%m/%Y}. Valor: R$ {cobranca.valor_total}."
            ),
            None,
            [destinatario],
            fail_silently=True,
        )

    return cobranca


def cobrancas_em_atraso(tenant):
    return Cobranca.objects.filter(
        tenant=tenant,
        status__in=[StatusCobranca.ABERTA, StatusCobranca.ATRASADA],
        vencimento__lt=timezone.localdate(),
    ).select_related("contrato")


def indicadores_de_inadimplencia(tenant, competencia=None):
    """Percentual inadimplente do mês KPI do dashboard."""

    competencia = primeiro_dia(competencia or timezone.localdate())
    do_mes = Cobranca.objects.filter(tenant=tenant, competencia=competencia).exclude(
        status=StatusCobranca.CANCELADA
    )

    total = do_mes.count()
    atrasadas = do_mes.filter(
        status__in=[StatusCobranca.ABERTA, StatusCobranca.ATRASADA],
        vencimento__lt=timezone.localdate(),
    ).count()

    return {
        "competencia": competencia,
        "total_cobrancas": total,
        "atrasadas": atrasadas,
        "percentual": round(atrasadas / total * 100, 2) if total else 0.0,
    }


def proxima_competencia_a_gerar(antecedencia_dias=10):
    """Gera com D-10 de antecedência, como manda o handoff."""

    alvo = timezone.localdate() + timedelta(days=antecedencia_dias)
    return primeiro_dia(alvo)
