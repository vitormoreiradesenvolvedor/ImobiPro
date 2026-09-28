from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    ConfirmarResetSenhaView,
    LoginView,
    LogoutView,
    PerfilView,
    RefreshView,
    SolicitarResetSenhaView,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register(r"usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", PerfilView.as_view(), name="me"),
    path("password-reset/", SolicitarResetSenhaView.as_view(), name="password-reset"),
    path(
        "password-reset/confirmar/",
        ConfirmarResetSenhaView.as_view(),
        name="password-reset-confirmar",
    ),
    path("", include(router.urls)),
]
