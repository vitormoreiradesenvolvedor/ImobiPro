from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.financeiro.views import (
    ConciliacaoView,
    RelatoriosView,
    ResumoFinanceiroView,
    TransacaoViewSet,
)

router = DefaultRouter()
router.register(r"transacoes", TransacaoViewSet, basename="transacao")

urlpatterns = [
    path("cobrancas/conciliar/", ConciliacaoView.as_view(), name="conciliar"),
    path("financeiro/resumo/", ResumoFinanceiroView.as_view(), name="resumo-financeiro"),
    path("relatorios/<str:relatorio>/", RelatoriosView.as_view(), name="relatorio"),
    path("", include(router.urls)),
]
