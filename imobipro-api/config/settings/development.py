# Import estrela é o padrão documentado do Django para settings por
# ambiente: o arquivo herda a base inteira e sobrescreve o que muda.
from .base import *  # noqa: F403  # NOSONAR

DEBUG = True

INSTALLED_APPS += ["django_extensions"]  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Em desenvolvimento o cookie de refresh trafega em HTTP local.
REFRESH_COOKIE_SECURE = False
REFRESH_COOKIE_SAMESITE = "Lax"
