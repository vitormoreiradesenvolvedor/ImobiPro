"""Lançamentos, estorno, DRE e conciliação bancária."""

import logging
import re
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.core.auditoria import Acao, registrar
from apps.core.money import dinheiro
from apps.financeiro.models import (
    CATEGORIAS_DE_PASSAGEM,
    CategoriaFinanceira,
    TipoTransacao,
    Transacao,
)

logger = logging.getLogger(__name__)


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 na API."""


def _usuario(request):
    usuario = getattr(request, "user", None)
    return usuario if usuario is not None and usuario.is_authenticated else None


def lancar(
    tenant, tipo, categoria, descricao, valor, competencia, request=None, **vinculos
):
    transacao = Transacao.objects.create(
        tenant=tenant,
        tipo=tipo,
        categoria=categoria,
        descricao=descricao,
        valor=dinheiro(valor),
        data_competencia=competencia,
        data_liquidacao=vinculos.pop("data_liquidacao", None),
        criado_por=_usuario(request),
        **vinculos,
    )
    registrar(
        transacao,
        Acao.CRIACAO,
        request=request,
        depois={"valor": str(transacao.valor), "categoria": categoria},
    )
    return transacao


def lancar_receita_de_cobranca(cobranca, request=None):
    """Uma baixa gera dois lançamentos: o aluguel (passagem) e a taxa (receita).

    Separar os dois é o que faz o DRE mostrar o que a imobiliária realmente
    ganhou, e não o volume que passou pela conta.
    """

    contrato = cobranca.contrato
    taxa = dinheiro(
        Decimal(str(cobranca.valor_aluguel))
        * Decimal(str(contrato.taxa_administracao_percent))
        / Decimal("100")
    )

    lancamentos = [
        lancar(
            contrato.tenant,
            TipoTransacao.RECEITA,
            CategoriaFinanceira.ALUGUEL,
            f"Aluguel recebido {contrato.numero} ({cobranca.competencia:%m/%Y})",
            cobranca.valor_pago or cobranca.valor_total,
            cobranca.competencia,
            request=request,
            cobranca=cobranca,
            contrato=contrato,
            data_liquidacao=cobranca.pago_em,
        ),
        lancar(
            contrato.tenant,
            TipoTransacao.RECEITA,
            CategoriaFinanceira.TAXA_ADMINISTRACAO,
            f"Taxa de administração {contrato.numero} ({cobranca.competencia:%m/%Y})",
            taxa,
            cobranca.competencia,
            request=request,
            cobranca=cobranca,
            contrato=contrato,
            data_liquidacao=cobranca.pago_em,
        ),
    ]
    return lancamentos


def lancar_despesa_de_repasse(repasse, request=None):
    return lancar(
        repasse.tenant,
        TipoTransacao.DESPESA,
        CategoriaFinanceira.REPASSE_PROPRIETARIO,
        f"Repasse ao proprietário {repasse.contrato.numero} ({repasse.competencia:%m/%Y})",
        repasse.valor_liquido,
        repasse.competencia,
        request=request,
        repasse=repasse,
        contrato=repasse.contrato,
        data_liquidacao=repasse.pago_em,
    )


def lancar_despesa_de_comissao(comissao, request=None):
    from apps.contratos.models import PapelComissao

    # A parte da imobiliária não é despesa: é o que sobra para ela.
    if comissao.papel == PapelComissao.IMOBILIARIA:
        return None

    return lancar(
        comissao.tenant,
        TipoTransacao.DESPESA,
        CategoriaFinanceira.FOLHA,
        f"Comissão {comissao.get_papel_display().lower()} {comissao.contrato.numero}",
        comissao.valor,
        comissao.contrato.assinado_em or timezone.localdate(),
        request=request,
        comissao=comissao,
        contrato=comissao.contrato,
        data_liquidacao=comissao.paga_em,
    )


@transaction.atomic
def estornar(transacao, motivo, request=None):
    """Transação nunca é deletada (handoff §1.7.3): estorna com contrapartida."""

    if transacao.estornada:
        raise RegraDeNegocio("Esta transação já foi estornada.")

    contrario = (
        TipoTransacao.DESPESA
        if transacao.tipo == TipoTransacao.RECEITA
        else TipoTransacao.RECEITA
    )

    estorno = Transacao.objects.create(
        tenant=transacao.tenant,
        tipo=contrario,
        categoria=transacao.categoria,
        descricao=f"Estorno: {transacao.descricao} {motivo}",
        valor=transacao.valor,
        data_competencia=transacao.data_competencia,
        data_liquidacao=timezone.localdate(),
        cobranca=transacao.cobranca,
        repasse=transacao.repasse,
        comissao=transacao.comissao,
        contrato=transacao.contrato,
        estorno_de=transacao,
        criado_por=_usuario(request),
    )
    registrar(
        estorno,
        Acao.CRIACAO,
        request=request,
        depois={"estorno_de": str(transacao.pk), "motivo": motivo},
    )
    return estorno


# ---------------------------------------------------------------------- DRE


def dre(tenant, inicio: date, fim: date):
    """Resultado do período, separando o que é dinheiro de terceiros."""

    # Estornos entram no cálculo: são movimento real e precisam zerar o
    # lançamento original. Escondê-los inflaria a receita do período.
    base = Transacao.objects.filter(
        tenant=tenant, data_competencia__gte=inicio, data_competencia__lte=fim
    )

    def somar(tipo, apenas_operacional):
        consulta = base.filter(tipo=tipo)
        if apenas_operacional:
            consulta = consulta.exclude(categoria__in=CATEGORIAS_DE_PASSAGEM)
        return dinheiro(consulta.aggregate(total=Sum("valor"))["total"] or 0)

    receita_operacional = somar(TipoTransacao.RECEITA, True)
    despesa_operacional = somar(TipoTransacao.DESPESA, True)

    por_categoria = {}
    for linha in (
        base.values("tipo", "categoria")
        .annotate(total=Sum("valor"))
        .order_by("tipo", "-total")
    ):
        rotulo = dict(CategoriaFinanceira.choices).get(
            linha["categoria"], linha["categoria"]
        )
        por_categoria.setdefault(linha["tipo"], {})[rotulo] = linha["total"]

    return {
        "inicio": inicio,
        "fim": fim,
        "receita_operacional": receita_operacional,
        "despesa_operacional": despesa_operacional,
        "resultado": dinheiro(receita_operacional - despesa_operacional),
        "margem_percentual": (
            round(
                float(
                    (receita_operacional - despesa_operacional) / receita_operacional * 100
                ),
                2,
            )
            if receita_operacional
            else 0.0
        ),
        "volume_movimentado": somar(TipoTransacao.RECEITA, False),
        "por_categoria": por_categoria,
    }


def fluxo_mensal(tenant, meses=12):
    """Série para o gráfico do dashboard."""

    from django.db.models.functions import TruncMonth

    inicio = timezone.localdate().replace(day=1)
    for _ in range(meses - 1):
        inicio = (inicio - timedelta(days=1)).replace(day=1)

    linhas = (
        Transacao.objects.filter(tenant=tenant, data_competencia__gte=inicio)
        .exclude(categoria__in=CATEGORIAS_DE_PASSAGEM)
        .annotate(mes=TruncMonth("data_competencia"))
        .values("mes", "tipo")
        .annotate(total=Sum("valor"))
        .order_by("mes")
    )

    serie = {}
    for linha in linhas:
        chave = linha["mes"].strftime("%Y-%m")
        serie.setdefault(chave, {"receita": 0, "despesa": 0})
        campo = "receita" if linha["tipo"] == TipoTransacao.RECEITA else "despesa"
        serie[chave][campo] = linha["total"]

    return [{"mes": mes, **valores} for mes, valores in sorted(serie.items())]


# ------------------------------------------------------- conciliação bancária


# CNAB é específico de cada banco. Este parser cobre o caso comum de retorno
# 400 posições (registro tipo 1) e serve de ponto de extensão por instituição.
POSICOES_CNAB400 = {
    "tipo_registro": (0, 1),
    "nosso_numero": (62, 73),
    "ocorrencia": (108, 110),
    "data_credito": (110, 116),
    "valor_pago": (253, 266),
}

OCORRENCIAS_DE_LIQUIDACAO = {"06", "07", "08", "17"}


def _decimal_cnab(bruto: str) -> Decimal:
    """Valores vêm sem separador decimal: os dois últimos dígitos são centavos."""
    somente_digitos = re.sub(r"\D", "", bruto) or "0"
    return dinheiro(Decimal(somente_digitos) / Decimal("100"))


def _data_cnab(bruto: str):
    bruto = re.sub(r"\D", "", bruto)
    if len(bruto) != 6:
        return None
    dia, mes, ano = int(bruto[0:2]), int(bruto[2:4]), int(bruto[4:6])
    return date(2000 + ano, mes, dia) if 1 <= mes <= 12 and 1 <= dia <= 31 else None


def conciliar_retorno_cnab(conteudo: str, tenant, request=None):
    """Baixa automática a partir do arquivo de retorno do banco.

    Retorna um relatório com o que foi conciliado e o que ficou pendente
    linha que não bate com cobrança nenhuma nunca é adivinhada.
    """

    from apps.locacao.models import Cobranca, StatusCobranca
    from apps.locacao.services import baixar_cobranca

    conciliadas, nao_encontradas, ja_pagas = [], [], []

    for linha in conteudo.splitlines():
        if len(linha) < 266 or linha[0] != "1":
            continue

        inicio, fim = POSICOES_CNAB400["ocorrencia"]
        if linha[inicio:fim] not in OCORRENCIAS_DE_LIQUIDACAO:
            continue

        inicio, fim = POSICOES_CNAB400["nosso_numero"]
        nosso_numero = linha[inicio:fim].strip().lstrip("0")

        inicio, fim = POSICOES_CNAB400["valor_pago"]
        valor = _decimal_cnab(linha[inicio:fim])

        inicio, fim = POSICOES_CNAB400["data_credito"]
        data_credito = _data_cnab(linha[inicio:fim]) or timezone.localdate()

        cobranca = Cobranca.objects.filter(
            tenant=tenant, nosso_numero__endswith=nosso_numero
        ).first()

        if not cobranca:
            nao_encontradas.append({"nosso_numero": nosso_numero, "valor": str(valor)})
            continue

        if cobranca.status == StatusCobranca.PAGA:
            ja_pagas.append({"nosso_numero": nosso_numero, "cobranca": str(cobranca.pk)})
            continue

        baixar_cobranca(
            cobranca, valor, data_pagamento=data_credito, forma="BOLETO", request=request
        )
        conciliadas.append({"cobranca": str(cobranca.pk), "valor": str(valor)})

    logger.info(
        "Conciliação CNAB: %s baixadas, %s sem correspondência.",
        len(conciliadas),
        len(nao_encontradas),
    )

    return {
        "conciliadas": conciliadas,
        "nao_encontradas": nao_encontradas,
        "ja_pagas": ja_pagas,
        "total_conciliado": len(conciliadas),
    }


def contas_a_receber(tenant, ate=None):
    from apps.locacao.models import Cobranca, StatusCobranca

    consulta = Cobranca.objects.filter(
        tenant=tenant, status__in=[StatusCobranca.ABERTA, StatusCobranca.ATRASADA]
    )
    if ate:
        consulta = consulta.filter(vencimento__lte=ate)
    return consulta


def contas_a_pagar(tenant):
    from apps.contratos.models import Comissao, StatusComissao
    from apps.locacao.models import Repasse, StatusRepasse

    repasses = Repasse.objects.filter(tenant=tenant, status=StatusRepasse.PENDENTE)
    comissoes = Comissao.objects.filter(
        tenant=tenant, status__in=[StatusComissao.PREVISTA, StatusComissao.LIBERADA]
    ).filter(~Q(papel="IMOBILIARIA"))

    return {
        "repasses": repasses,
        "comissoes": comissoes,
        "total": dinheiro(
            (repasses.aggregate(t=Sum("valor_liquido"))["t"] or 0)
            + (comissoes.aggregate(t=Sum("valor"))["t"] or 0)
        ),
    }
