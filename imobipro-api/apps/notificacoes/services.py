"""Criação e entrega de notificações.

A notificação sempre é gravada; o empurrão pelo WebSocket é melhor-esforço
se o Redis estiver fora, o usuário ainda vê o aviso ao abrir o sino.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.notificacoes.models import Notificacao

logger = logging.getLogger(__name__)


def grupo_do_usuario(usuario_id) -> str:
    return f"usuario-{usuario_id}"


def notificar_usuario(usuario, tipo, titulo, descricao="", dados=None):
    if usuario is None or usuario.tenant_id is None:
        return None

    notificacao = Notificacao.objects.create(
        tenant_id=usuario.tenant_id,
        usuario=usuario,
        tipo=tipo,
        titulo=titulo,
        descricao=descricao,
        dados=dados or {},
    )

    empurrar(notificacao)
    return notificacao


def empurrar(notificacao):
    """Envia para o canal do usuário. Falha de transporte não quebra o fluxo."""

    camada = get_channel_layer()
    if camada is None:
        return

    payload = {
        "type": "notificacao",
        "id": str(notificacao.pk),
        "tipo": notificacao.tipo,
        "titulo": notificacao.titulo,
        "descricao": notificacao.descricao,
        "dados": notificacao.dados,
        "criado_em": notificacao.criado_em.isoformat(),
    }

    try:
        async_to_sync(camada.group_send)(grupo_do_usuario(notificacao.usuario_id), payload)
    except Exception as falha:  # pragma: no cover - indisponibilidade do Redis
        logger.warning("Notificação %s não foi empurrada: %s", notificacao.pk, falha)


def notificar_equipe(tenant, papeis, tipo, titulo, descricao="", dados=None):
    """Avisa todos os usuários ativos de determinados papéis (ex.: gerentes)."""

    from apps.accounts.models import Usuario

    destinatarios = Usuario.objects.filter(tenant=tenant, papel__in=papeis, ativo=True)
    return [
        notificar_usuario(usuario, tipo, titulo, descricao, dados)
        for usuario in destinatarios
    ]
