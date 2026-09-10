"""Mixins de ViewSet reutilizados por todos os módulos de domínio."""

from apps.core.middleware import tenant_do_request


class TenantQuerySetMixin:
    """Restringe o queryset ao tenant do usuário autenticado.

    Invariante do sistema (handoff §1.7.5): nenhum dado é filtrado por tenant
    manualmente dentro de uma view. Quem não tem tenant resolvido não vê nada.
    O SUPERADMIN da plataforma é a única exceção e vê todos os tenants.
    """

    campo_tenant = "tenant"

    def get_queryset(self):
        queryset = super().get_queryset()
        usuario = self.request.user

        if getattr(usuario, "is_superadmin", False):
            return queryset

        tenant = tenant_do_request(self.request)
        if tenant is None:
            return queryset.none()

        return queryset.filter(**{self.campo_tenant: tenant})

    def perform_create(self, serializer):
        serializer.save(**{self.campo_tenant: tenant_do_request(self.request)})
