from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import Papel

PODEM_EDITAR = {Papel.ADMIN, Papel.GERENTE, Papel.CORRETOR, Papel.SUPERADMIN}


class ImovelPermission(BasePermission):
    """Financeiro consulta a carteira, mas não altera imóvel."""

    message = "Seu papel não permite alterar imóveis."

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return usuario.papel in PODEM_EDITAR

    def has_object_permission(self, request, view, obj):
        usuario = request.user
        if request.method in SAFE_METHODS:
            return True
        # Corretor mexe no que captou; gestão mexe em tudo.
        if usuario.papel == Papel.CORRETOR:
            return obj.captador_id == usuario.id
        return usuario.papel in PODEM_EDITAR
