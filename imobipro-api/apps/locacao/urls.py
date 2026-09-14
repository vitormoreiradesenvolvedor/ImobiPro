from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.locacao.views import CobrancaViewSet, RepasseViewSet

router = DefaultRouter()
router.register(r"cobrancas", CobrancaViewSet, basename="cobranca")
router.register(r"repasses", RepasseViewSet, basename="repasse")

urlpatterns = [path("", include(router.urls))]
