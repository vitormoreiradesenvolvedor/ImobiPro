from django.urls import path

from apps.onboarding.views import (
    ConcluirTourView,
    DispensarView,
    ProgressoOnboardingView,
    ReiniciarView,
)

urlpatterns = [
    path("onboarding/", ProgressoOnboardingView.as_view(), name="onboarding"),
    path(
        "onboarding/tours/<str:identificador>/concluir/",
        ConcluirTourView.as_view(),
        name="onboarding-concluir-tour",
    ),
    path("onboarding/dispensar/", DispensarView.as_view(), name="onboarding-dispensar"),
    path("onboarding/reiniciar/", ReiniciarView.as_view(), name="onboarding-reiniciar"),
]
