import tempfile

# Import estrela é o padrão documentado do Django para settings por
# ambiente: o arquivo herda a base inteira e sobrescreve o que muda.
from .base import *  # noqa: F403  # NOSONAR

DEBUG = False

# Uploads da suíte vão para um diretório descartável, nunca para media/.
MEDIA_ROOT = tempfile.mkdtemp(prefix="imobipro-test-media-")

# Hash barato: a suíte não deve gastar tempo em Argon2.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

REFRESH_COOKIE_SECURE = False
REFRESH_COOKIE_SAMESITE = "Lax"

# Mantém os mesmos escopos de produção, com teto alto: a suíte não deve
# esbarrar em throttling, mas escopo faltando aqui vira 500 só em teste.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = dict.fromkeys(  # noqa: F405
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
    "10000/min",  # noqa: F405
)
