from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import PAPEIS_INTERNOS, Papel


class AcessoAoPainel(BasePermission):
    """Permissão padrão da API interna: só quem opera a imobiliária.

    Inquilino e proprietário também têm login (portal do cliente), e sem esta
    barreira eles alcançariam a carteira inteira e as cobranças de todo mundo
    apenas por estarem autenticados no mesmo tenant. As telas do portal e as
    rotas públicas declaram a própria permissão e não passam por aqui.
    """

    message = "Este acesso é do portal do cliente, não do painel da imobiliária."

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario.is_authenticated:
            return False
        return usuario.papel in PAPEIS_INTERNOS or usuario.is_superadmin


class PodeGerenciarUsuarios(BasePermission):
    """Leitura para qualquer usuário interno; escrita só para ADMIN/SUPERADMIN."""

    message = "Seu papel não permite gerenciar usuários."

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return usuario.eh_interno or usuario.is_superadmin
        return usuario.papel in {Papel.ADMIN, Papel.SUPERADMIN}


class EhSuperadmin(BasePermission):
    message = "Restrito ao operador da plataforma."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superadmin
