from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.imoveis.views import CaracteristicaViewSet, ImovelViewSet

router = DefaultRouter()
router.register(r"imoveis", ImovelViewSet, basename="imovel")
router.register(r"caracteristicas", CaracteristicaViewSet, basename="caracteristica")

urlpatterns = [path("", include(router.urls))]
