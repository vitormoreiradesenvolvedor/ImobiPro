"""Rotas públicas do atendimento, sob /api/v1/public/<subdominio>/."""

from django.urls import path

from apps.atendimento.views import AberturaTicketPublicaView, AcompanhamentoPublicoView

urlpatterns = [
    path("tickets/", AberturaTicketPublicaView.as_view(), name="ticket-publico-abrir"),
    path(
        "tickets/<str:protocolo>/",
        AcompanhamentoPublicoView.as_view(),
        name="ticket-publico-acompanhar",
    ),
]
