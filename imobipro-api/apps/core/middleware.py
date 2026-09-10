"""Resolução do tenant a partir do JWT."""

import logging

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

CLAIM_TENANT = "tenant_id"


class TenantMiddleware:
    """Injeta ``request.tenant`` e ``request.tenant_id`` a partir do access token.

    O middleware não autentica nem bloqueia nada: quem faz isso é o DRF.
    Ele apenas deixa o tenant disponível antes da view, para que
    ``TenantQuerySetMixin`` e o log de auditoria não precisem repetir a lógica.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.autenticacao = JWTAuthentication()

    def __call__(self, request):
        request.tenant = None
        request.tenant_id = None

        header = self.autenticacao.get_header(request)
        if header is not None:
            token_bruto = self.autenticacao.get_raw_token(header)
            if token_bruto is not None:
                try:
                    token = self.autenticacao.get_validated_token(token_bruto)
                    request.tenant_id = token.get(CLAIM_TENANT)
                except (InvalidToken, TokenError):
                    # Token inválido/expirado é tratado pelo DRF com 401.
                    logger.debug("Token inválido ao resolver tenant.")

        return self.get_response(request)


def tenant_do_request(request):
    """Tenant efetivo da requisição, com o usuário autenticado como fonte final.

    O claim do token serve a views não-DRF; para views DRF o usuário já foi
    resolvido e é a fonte mais confiável (cobre troca de tenant e desativação).
    """

    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return usuario.tenant
    return None
