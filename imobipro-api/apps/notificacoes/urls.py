from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notificacoes.views import NotificacaoViewSet

router = DefaultRouter()
router.register(r"notificacoes", NotificacaoViewSet, basename="notificacao")

urlpatterns = [path("", include(router.urls))]
