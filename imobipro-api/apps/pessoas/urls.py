from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.pessoas.views import ConsultaCepView, PessoaViewSet

router = DefaultRouter()
router.register(r"pessoas", PessoaViewSet, basename="pessoa")

urlpatterns = [
    path("pessoas/cep/<str:cep>/", ConsultaCepView.as_view(), name="consulta-cep"),
    path("", include(router.urls)),
]
