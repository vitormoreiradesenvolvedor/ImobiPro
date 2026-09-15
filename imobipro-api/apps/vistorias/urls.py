from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.vistorias.views import VistoriaViewSet

router = DefaultRouter()
router.register(r"vistorias", VistoriaViewSet, basename="vistoria")

urlpatterns = [path("", include(router.urls))]
