"""Rotinas de contrato: aviso de vencimento e reajuste anual."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Percentuais acumulados do índice. Em produção vêm da integração com a FGV/IBGE;
# até lá o gestor confirma o número na tela de reajuste.
INDICES_PADRAO = {"IGPM": 4.5, "IPCA": 4.0, "INPC": 4.0}


@shared_task(name="contratos.alertar_contratos_a_vencer")
def alertar_contratos_a_vencer():
    """Avisa em 90, 60 e 30 dias janela de renegociação com o proprietário."""

    from apps.accounts.models import Papel, Tenant
    from apps.contratos.services import contratos_a_vencer
    from apps.notificacoes.models import TipoNotificacao
    from apps.notificacoes.services import notificar_equipe

    avisados = 0
    for tenant in Tenant.objects.filter(ativo=True):
        for contrato in contratos_a_vencer(tenant, dias=90):
            if contrato.dias_para_vencer not in {90, 60, 30}:
                continue
            notificar_equipe(
                tenant,
                [Papel.ADMIN, Papel.GERENTE],
                tipo=TipoNotificacao.CONTRATO_A_VENCER,
                titulo=f"{contrato.numero} vence em {contrato.dias_para_vencer} dias",
                descricao=f"{contrato.imovel.codigo} {contrato.imovel.titulo}.",
                dados={"contrato_id": str(contrato.pk)},
            )
            avisados += 1

    return avisados


@shared_task(name="contratos.aplicar_reajustes_anuais")
def aplicar_reajustes_anuais():
    """Aplica o reajuste no aniversário do contrato e gera o aditivo."""

    from apps.contratos.models import Contrato, IndiceReajuste, StatusContrato
    from apps.contratos.services import aplicar_reajuste

    hoje = timezone.localdate()
    aplicados = 0

    ativos = Contrato.objects.filter(status=StatusContrato.ATIVO, tipo="LOCACAO").exclude(
        indice_reajuste=IndiceReajuste.SEM_REAJUSTE
    )

    for contrato in ativos:
        vencimento = contrato.proximo_reajuste_em
        if vencimento and vencimento <= hoje:
            aplicar_reajuste(contrato, INDICES_PADRAO.get(contrato.indice_reajuste, 0))
            aplicados += 1

    if aplicados:
        logger.info("Reajuste anual aplicado em %s contratos.", aplicados)
    return aplicados


@shared_task(name="contratos.encerrar_contratos_vencidos")
def encerrar_contratos_vencidos():
    from apps.contratos.models import Contrato, StatusContrato
    from apps.contratos.services import encerrar_contrato

    vencidos = Contrato.objects.filter(
        status=StatusContrato.ATIVO,
        data_fim__isnull=False,
        data_fim__lt=timezone.localdate(),
    )
    total = 0
    for contrato in vencidos:
        encerrar_contrato(contrato)
        total += 1
    return total
