from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.integracoes.views import (
    EventoIntegracaoViewSet,
    IntegracaoPortalViewSet,
    WebhookLeadView,
)

router = DefaultRouter()
router.register(
    r"integracoes/portais", IntegracaoPortalViewSet, basename="integracao-portal"
)
router.register(
    r"integracoes/eventos", EventoIntegracaoViewSet, basename="evento-integracao"
)

urlpatterns = [
    path(
        "leads/webhook/<str:portal>/<str:subdominio>/",
        WebhookLeadView.as_view(),
        name="webhook-lead",
    ),
    path("", include(router.urls)),
]
