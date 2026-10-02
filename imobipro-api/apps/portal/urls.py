"""Rotas do portal do cliente, sob /api/v1/meu/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.portal.views import (
    AssinarVistoriaView,
    ContratoEmPdfView,
    MeusChamadosViewSet,
    MeusContratosViewSet,
    MinhasCobrancasViewSet,
    MinhasVistoriasViewSet,
    ResumoDoClienteView,
)

router = DefaultRouter()
router.register(r"contratos", MeusContratosViewSet, basename="meu-contrato")
router.register(r"cobrancas", MinhasCobrancasViewSet, basename="minha-cobranca")
router.register(r"vistorias", MinhasVistoriasViewSet, basename="minha-vistoria")
router.register(r"chamados", MeusChamadosViewSet, basename="meu-chamado")

urlpatterns = [
    path("resumo/", ResumoDoClienteView.as_view(), name="meu-resumo"),
    path(
        "vistorias/<uuid:vistoria_id>/assinar/",
        AssinarVistoriaView.as_view(),
        name="minha-vistoria-assinar",
    ),
    path(
        "contratos/<uuid:contrato_id>/pdf/",
        ContratoEmPdfView.as_view(),
        name="meu-contrato-pdf",
    ),
    path("", include(router.urls)),
]
