from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.views import IdentidadePublicaView
from apps.core.views import health
from apps.crm.views import ContatoPublicoView

# Prefixo único da API versionada.
API = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(f"{API}auth/", include("apps.accounts.urls")),
    path(API, include("apps.pessoas.urls")),
    path(API, include("apps.imoveis.urls")),
    path(API, include("apps.crm.urls")),
    path(API, include("apps.contratos.urls")),
    path(API, include("apps.locacao.urls")),
    path(API, include("apps.vistorias.urls")),
    path(API, include("apps.financeiro.urls")),
    path(API, include("apps.integracoes.urls")),
    path(API, include("apps.notificacoes.urls")),
    path(API, include("apps.onboarding.urls")),
    path(API, include("apps.atendimento.urls")),
    path(API, include("apps.candidaturas.urls")),
    path(f"{API}meu/", include("apps.portal.urls")),
    path(
        f"{API}public/<str:subdominio>/identidade/",
        IdentidadePublicaView.as_view(),
        name="identidade-publica",
    ),
    path(f"{API}public/<str:subdominio>/", include("apps.imoveis.public_urls")),
    path(f"{API}public/<str:subdominio>/", include("apps.atendimento.public_urls")),
    path(f"{API}public/<str:subdominio>/", include("apps.candidaturas.public_urls")),
    path(
        f"{API}public/<str:subdominio>/contato/",
        ContatoPublicoView.as_view(),
        name="contato-publico",
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("health/", health, name="health"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
