"""Vigilância do SLA e lembretes de agenda."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="crm.verificar_sla_de_atendimento")
def verificar_sla_de_atendimento():
    """Roda a cada 5 minutos: devolve para a fila o lead sem primeiro contato."""

    from apps.accounts.models import Tenant
    from apps.crm.services import devolver_lead_para_fila, leads_com_sla_estourado

    devolvidos = 0
    for tenant in Tenant.objects.filter(ativo=True):
        for lead in leads_com_sla_estourado(tenant):
            devolver_lead_para_fila(lead)
            devolvidos += 1

    if devolvidos:
        logger.info("SLA: %s leads devolvidos para a fila.", devolvidos)
    return devolvidos


@shared_task(name="crm.avisar_sla_proximo_do_limite")
def avisar_sla_proximo_do_limite(minutos_de_antecedencia=5):
    """Cutuca o corretor antes de o SLA estourar melhor prevenir que remanejar."""

    from apps.crm.models import MINUTOS_SLA_PRIMEIRO_CONTATO as SLA
    from apps.crm.models import EstagioLead, Lead
    from apps.notificacoes.models import TipoNotificacao
    from apps.notificacoes.services import notificar_usuario

    agora = timezone.now()
    inicio = agora - timedelta(minutes=SLA)
    fim = agora - timedelta(minutes=SLA - minutos_de_antecedencia)

    em_risco = Lead.objects.filter(
        primeiro_contato_em__isnull=True,
        estagio=EstagioLead.NOVO,
        corretor__isnull=False,
        atribuido_em__gte=inicio,
        atribuido_em__lt=fim,
    ).select_related("corretor")

    for lead in em_risco:
        notificar_usuario(
            lead.corretor,
            tipo=TipoNotificacao.SLA_ESTOURANDO,
            titulo=f"Fale com {lead.nome} agora",
            descricao=f"O SLA de {SLA} minutos está acabando.",
            dados={"lead_id": str(lead.pk)},
        )

    return em_risco.count()


@shared_task(name="crm.lembrar_visitas_do_dia")
def lembrar_visitas_do_dia():
    from apps.crm.models import Visita
    from apps.notificacoes.models import TipoNotificacao
    from apps.notificacoes.services import notificar_usuario

    hoje = timezone.localdate()
    visitas = Visita.objects.filter(
        agendada_para__date=hoje, cancelada=False, realizada=False
    ).select_related("lead", "imovel", "corretor")

    for visita in visitas:
        if not visita.corretor_id:
            continue
        notificar_usuario(
            visita.corretor,
            tipo=TipoNotificacao.VISITA_HOJE,
            titulo=f"Visita hoje às {visita.agendada_para:%H:%M}",
            descricao=f"{visita.lead.nome} em {visita.imovel.codigo}.",
            dados={"visita_id": str(visita.pk), "lead_id": str(visita.lead_id)},
        )

    return visitas.count()


@shared_task(name="crm.expirar_propostas_vencidas")
def expirar_propostas_vencidas():
    from apps.crm.models import Proposta, StatusProposta

    return Proposta.objects.filter(
        status=StatusProposta.ENVIADA, validade__lt=timezone.localdate()
    ).update(status=StatusProposta.EXPIRADA)
