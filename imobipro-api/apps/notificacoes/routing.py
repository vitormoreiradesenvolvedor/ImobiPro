from django.urls import path

from apps.notificacoes.consumers import NotificacoesConsumer

websocket_urlpatterns = [
    path("ws/notificacoes/", NotificacoesConsumer.as_asgi()),
]
