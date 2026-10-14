"""Rotinas mensais de locação: geração de cobrança e régua de inadimplência."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="locacao.gerar_cobrancas_mensais")
def gerar_cobrancas_mensais(antecedencia_dias=10):
    """D-10: cria a cobrança do mês seguinte para todo contrato ativo."""

    from apps.contratos.models import Contrato, StatusContrato, TipoContrato
    from apps.locacao.services import gerar_cobranca, proxima_competencia_a_gerar

    geradas = 0
    ativos = Contrato.objects.filter(
        status=StatusContrato.ATIVO, tipo=TipoContrato.LOCACAO
    ).select_related("imovel")

    for contrato in ativos:
        competencia = proxima_competencia_a_gerar(antecedencia_dias)
        if contrato.data_fim and competencia > contrato.data_fim:
            continue
        cobranca = gerar_cobranca(contrato, competencia)
        geradas += int(cobranca.criado_em.date() == competencia.today())

    logger.info("Cobranças verificadas em %s contratos ativos.", ativos.count())
    return geradas


@shared_task(name="locacao.executar_regua_de_inadimplencia")
def executar_regua_de_inadimplencia():
    """D+1, D+5, D+15, D+30 cada etapa dispara uma vez só."""

    from apps.accounts.models import Papel, Tenant
    from apps.locacao.services import (
        cobrancas_em_atraso,
        etapa_devida,
        executar_etapa_da_regua,
    )
    from apps.notificacoes.models import TipoNotificacao
    from apps.notificacoes.services import notificar_equipe

    disparos = 0
    for tenant in Tenant.objects.filter(ativo=True):
        for cobranca in cobrancas_em_atraso(tenant):
            etapa = etapa_devida(cobranca)
            if not etapa:
                continue

            executar_etapa_da_regua(cobranca, etapa)
            disparos += 1

            if etapa == "JURIDICO":
                notificar_equipe(
                    tenant,
                    [Papel.ADMIN, Papel.FINANCEIRO],
                    tipo=TipoNotificacao.COBRANCA_ATRASADA,
                    titulo=f"Encaminhar ao jurídico: {cobranca.contrato.numero}",
                    descricao=f"{cobranca.dias_de_atraso} dias de atraso.",
                    dados={"cobranca_id": str(cobranca.pk)},
                )

    return disparos


@shared_task(name="locacao.marcar_cobrancas_atrasadas")
def marcar_cobrancas_atrasadas():
    from django.utils import timezone

    from apps.locacao.models import Cobranca, StatusCobranca

    return Cobranca.objects.filter(
        status=StatusCobranca.ABERTA, vencimento__lt=timezone.localdate()
    ).update(status=StatusCobranca.ATRASADA)
