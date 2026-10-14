from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.contratos.views import (
    ComissaoViewSet,
    ConfiguracaoComissaoView,
    ContratoViewSet,
)

router = DefaultRouter()
router.register(r"contratos", ContratoViewSet, basename="contrato")
router.register(r"comissoes", ComissaoViewSet, basename="comissao")
router.register(
    r"configuracoes/comissao", ConfiguracaoComissaoView, basename="config-comissao"
)

urlpatterns = [path("", include(router.urls))]
