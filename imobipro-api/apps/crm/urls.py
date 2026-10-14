from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.crm.views import LeadViewSet, PropostaViewSet, VisitaViewSet

router = DefaultRouter()
router.register(r"leads", LeadViewSet, basename="lead")
router.register(r"visitas", VisitaViewSet, basename="visita")
router.register(r"propostas", PropostaViewSet, basename="proposta")

urlpatterns = [path("", include(router.urls))]
