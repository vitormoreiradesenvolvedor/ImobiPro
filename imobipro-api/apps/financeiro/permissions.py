from rest_framework.permissions import BasePermission

from apps.accounts.models import Papel

PAPEIS_FINANCEIROS = {Papel.ADMIN, Papel.FINANCEIRO, Papel.SUPERADMIN}


class PodeVerFinanceiro(BasePermission):
    """Corretor e gerente não entram no módulo de dinheiro."""

    message = "Módulo financeiro restrito ao financeiro e à administração."

    def has_permission(self, request, view):
        usuario = request.user
        return usuario.is_authenticated and usuario.papel in PAPEIS_FINANCEIROS
