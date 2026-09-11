"""Rotas da vitrine pública, montadas sob /api/v1/public/<subdominio>/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.imoveis.views import ImovelPublicoViewSet

router = DefaultRouter()
router.register(r"imoveis", ImovelPublicoViewSet, basename="imovel-publico")

urlpatterns = [path("", include(router.urls))]
