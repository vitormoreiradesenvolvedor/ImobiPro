from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.candidaturas.views import CandidaturaViewSet

router = DefaultRouter()
router.register(r"candidaturas", CandidaturaViewSet, basename="candidatura")

urlpatterns = [path("", include(router.urls))]
