"""
Configurações comuns a todos os ambientes.

Herda o padrão da disciplina (LANGUAGE_CODE pt-BR, TIME_ZONE America/Sao_Paulo,
DRF com router/viewset) e endurece o que o repositório de aula deixa aberto:
segredos fora do código, CORS explícito, autenticação obrigatória.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173"]),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------- aplicações

DJANGO_APPS = [
    # O Unfold entra antes do admin: ele sobrescreve os templates padrão.
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Busca textual (GIN/tsvector) e tipos específicos do PostgreSQL.
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.pessoas",
    "apps.imoveis",
    "apps.crm",
    "apps.contratos",
    "apps.locacao",
    "apps.vistorias",
    "apps.financeiro",
    "apps.integracoes",
    "apps.notificacoes",
    "apps.onboarding",
    "apps.atendimento",
    "apps.candidaturas",
    "apps.portal",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.TenantMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ------------------------------------------------------------------- banco

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------- autenticação

AUTH_USER_MODEL = "accounts.Usuario"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------- DRF

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("apps.accounts.permissions.AcessoAoPainel",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.PaginacaoPadrao",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler_padrao",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    # O identificador do cliente vem do X-Forwarded-For quando a aplicação está
    # atrás de proxy. Sem isto, todo mundo chega com o IP do proxy e um único
    # visitante consome o limite da aplicação inteira.
    "NUM_PROXIES": env.int("NUM_PROXIES", default=1),
    # Os limites são configuráveis por ambiente, com o padrão de produção
    # embutido: só o ambiente de desenvolvimento afrouxa o login (a suíte E2E
    # autentica dezenas de vezes por minuto). Em produção, 5/min continua valendo.
    "DEFAULT_THROTTLE_RATES": {
        # Vitrine pública e páginas de imóvel são anônimas e navegadas às dezenas
        # por visita: um teto baixo aqui derruba visitante legítimo.
        "anon": env("THROTTLE_ANON", default="600/hour"),
        "user": env("THROTTLE_USER", default="1000/hour"),
        "login": env("THROTTLE_LOGIN", default="5/min"),
        # Cadastre-se cria imobiliária: poucas por hora bastam para gente de
        # verdade e travam robô criando tenant em massa.
        "cadastro": env("THROTTLE_CADASTRO", default="10/hour"),
        # Renovação de sessão tem balde próprio: a SPA renova a cada carga de
        # página, e esse tráfego não pode competir com a navegação anônima nem
        # bloquear quem acabou de sair e entrar de novo.
        "refresh": env("THROTTLE_REFRESH", default="60/min"),
        # Formulário do site público: limite apertado contra robô de spam.
        "contato_publico": env("THROTTLE_CONTATO_PUBLICO", default="10/hour"),
        # Consultar o próprio protocolo ou reenviar documento não é spam: quem
        # está acompanhando um pedido atualiza a página várias vezes, e travar
        # isso no mesmo balde do formulário deixaria o cliente sem resposta.
        "acompanhamento_publico": env("THROTTLE_ACOMPANHAMENTO", default="120/hour"),
        # Webhook de portal é servidor-a-servidor: volume maior, ainda limitado.
        "webhook_portal": env("THROTTLE_WEBHOOK", default="600/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.LoginSerializer",
}

# Nome do cookie HttpOnly que carrega o refresh token.
REFRESH_COOKIE_NAME = "imobipro_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth/"

SPECTACULAR_SETTINGS = {
    "TITLE": "ImobiPro API",
    "DESCRIPTION": "API de gestão imobiliária Django REST Framework.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ------------------------------------------------------------------- CORS

# A política de uso do Nominatim exige identificar a aplicação e um contato
# real no User-Agent. Sai por ambiente: cada instalação responde pelo próprio uso.
CONTATO_GEOCODIFICACAO = env("CONTATO_GEOCODIFICACAO", default="suporte@imobipro.app")

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# ------------------------------------------------------------------ Celery

CELERY_BROKER_URL = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_URL", default="redis://redis:6379/0")]},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/1"),
    }
}

# ------------------------------------------------------- i18n / arquivos

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Limite de upload fotos de imóvel entram por aqui.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verboso": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verboso"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}


# ------------------------------------------------------- ambiente administrativo

# O Django Admin é a mesa de trabalho da operação interna, não uma tela de
# depuração: tema próprio, navegação por módulo e a cor da plataforma. O tema
# acompanha o sistema operacional de quem abre, como no painel.
UNFOLD = {
    "SITE_TITLE": "ImobiPro",
    "SITE_HEADER": "ImobiPro",
    "SITE_SUBHEADER": "Administração da plataforma",
    "SITE_SYMBOL": "apartment",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "COLORS": {
        "primary": {
            "50": "240 253 250",
            "100": "204 251 241",
            "200": "153 246 228",
            "300": "94 234 212",
            "400": "45 212 191",
            "500": "20 184 166",
            "600": "13 148 136",
            "700": "15 118 110",
            "800": "17 94 89",
            "900": "19 78 74",
            "950": "4 47 46",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Carteira",
                "separator": True,
                "items": [
                    {
                        "title": "Imóveis",
                        "icon": "home_work",
                        "link": "/admin/imoveis/imovel/",
                    },
                    {"title": "Pessoas", "icon": "group", "link": "/admin/pessoas/pessoa/"},
                ],
            },
            {
                "title": "Comercial",
                "separator": True,
                "items": [
                    {"title": "Leads", "icon": "trending_up", "link": "/admin/crm/lead/"},
                    {"title": "Visitas", "icon": "event", "link": "/admin/crm/visita/"},
                    {
                        "title": "Contratos",
                        "icon": "description",
                        "link": "/admin/contratos/contrato/",
                    },
                    {
                        "title": "Atendimentos",
                        "icon": "support_agent",
                        "link": "/admin/atendimento/ticket/",
                    },
                    {
                        "title": "Candidaturas",
                        "icon": "assignment_ind",
                        "link": "/admin/candidaturas/candidatura/",
                    },
                ],
            },
            {
                "title": "Financeiro",
                "separator": True,
                "items": [
                    {
                        "title": "Cobranças",
                        "icon": "request_quote",
                        "link": "/admin/locacao/cobranca/",
                    },
                    {
                        "title": "Repasses",
                        "icon": "payments",
                        "link": "/admin/locacao/repasse/",
                    },
                    {
                        "title": "Comissões",
                        "icon": "percent",
                        "link": "/admin/contratos/comissao/",
                    },
                ],
            },
            {
                "title": "Plataforma",
                "separator": True,
                "items": [
                    {
                        "title": "Imobiliárias",
                        "icon": "domain",
                        "link": "/admin/accounts/tenant/",
                    },
                    {
                        "title": "Usuários",
                        "icon": "badge",
                        "link": "/admin/accounts/usuario/",
                    },
                    {
                        "title": "Auditoria",
                        "icon": "history",
                        "link": "/admin/core/logauditoria/",
                    },
                ],
            },
        ],
    },
}
