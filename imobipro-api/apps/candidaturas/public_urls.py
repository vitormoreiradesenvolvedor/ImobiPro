"""Portal do pretendente, sob /api/v1/public/<subdominio>/."""

from django.urls import path

from apps.candidaturas.views import PortalCandidaturaView

urlpatterns = [
    path(
        "candidatura/<str:token>/",
        PortalCandidaturaView.as_view(),
        name="candidatura-portal",
    ),
]
