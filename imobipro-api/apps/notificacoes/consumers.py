"""WebSocket de notificações: ws://host/ws/notificacoes/?token=<jwt>."""

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.notificacoes.services import grupo_do_usuario


@database_sync_to_async
def _usuario_do_token(token_bruto):
    from apps.accounts.models import Usuario

    try:
        token = AccessToken(token_bruto)
    except TokenError:
        return None

    return Usuario.objects.filter(pk=token["user_id"], ativo=True).first()


class NotificacoesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        bruto = self.scope.get("query_string", b"").decode()
        parametros = {
            par.split("=", 1)[0]: par.split("=", 1)[1]
            for par in bruto.split("&")
            if "=" in par
        }
        usuario = await _usuario_do_token(parametros.get("token", ""))

        if usuario is None:
            # 4401: mesma semântica do 401 HTTP, para o front saber renovar.
            await self.close(code=4401)
            return

        self.usuario = usuario
        self.grupo = grupo_do_usuario(usuario.pk)
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()
        await self.send(json.dumps({"tipo": "CONECTADO", "usuario": str(usuario.pk)}))

    async def disconnect(self, code):
        if grupo := getattr(self, "grupo", None):
            await self.channel_layer.group_discard(grupo, self.channel_name)

    async def notificacao(self, evento):
        """Handler do `group_send` o `type` da mensagem aponta para cá."""
        await self.send(json.dumps({k: v for k, v in evento.items() if k != "type"}))
