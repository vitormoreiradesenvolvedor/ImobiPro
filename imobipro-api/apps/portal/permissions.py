from rest_framework.permissions import BasePermission

from apps.accounts.models import Papel


class EhClienteComAcesso(BasePermission):
    """Inquilino ou proprietário com cadastro vinculado.

    O vínculo com a pessoa é obrigatório: sem ele não há como saber quais
    contratos são desse cliente, e devolver dado de outra pessoa é o pior erro
    possível num portal.
    """

    message = "Este acesso não está vinculado a um cadastro."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            usuario.is_authenticated
            and usuario.papel in {Papel.INQUILINO, Papel.PROPRIETARIO}
            and usuario.pessoa_id
            and usuario.tenant_id
        )
