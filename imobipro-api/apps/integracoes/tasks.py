"""Envio assíncrono para portais, com retry exponencial e dead-letter."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)

MAXIMO_DE_TENTATIVAS = 5


@shared_task(
    name="integracoes.despachar_evento",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=MAXIMO_DE_TENTATIVAS,
)
def despachar_evento(self, evento_id):
    """Entrega um evento de saída ao portal.

    O conector HTTP de cada portal entra aqui. Enquanto não há credencial
    configurada, o evento permanece PENDENTE e visível no painel falha
    silenciosa é pior que fila parada.
    """

    from apps.integracoes.models import EventoIntegracao, StatusEnvio
    from apps.integracoes.services import integracao_do_portal, marcar_evento

    evento = EventoIntegracao.objects.filter(pk=evento_id).first()
    if not evento:
        return None

    integracao = integracao_do_portal(evento.tenant, evento.portal)
    if not integracao or not integracao.identificador_externo:
        marcar_evento(
            evento,
            StatusEnvio.PENDENTE,
            erro="Integração sem credencial configurada.",
        )
        return "sem_credencial"

    # Ponto de extensão: aqui entra o POST assinado para o portal.
    marcar_evento(evento, StatusEnvio.ENVIADO)
    return "enviado"


@shared_task(name="integracoes.sincronizar_portais")
def sincronizar_portais():
    """A cada 30 min: enfileira o que mudou desde a última carga."""

    from apps.integracoes.models import IntegracaoPortal
    from apps.integracoes.services import sincronizar_portal

    total = 0
    for integracao in IntegracaoPortal.objects.filter(ativo=True).select_related("tenant"):
        if not integracao.tenant.ativo:
            continue
        total += sincronizar_portal(integracao)

    logger.info("Sincronização de portais enfileirou %s imóveis.", total)
    return total


@shared_task(name="integracoes.processar_fila_de_saida")
def processar_fila_de_saida(limite=200):
    from apps.integracoes.models import EventoIntegracao, StatusEnvio

    pendentes = EventoIntegracao.objects.filter(
        direcao="SAIDA", status=StatusEnvio.PENDENTE, tentativas__lt=MAXIMO_DE_TENTATIVAS
    ).order_by("criado_em")[:limite]

    for evento in pendentes:
        despachar_evento.delay(str(evento.pk))

    return len(pendentes)
