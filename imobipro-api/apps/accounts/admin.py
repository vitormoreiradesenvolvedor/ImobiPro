from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin

from apps.accounts.models import Tenant, Usuario


@admin.register(Tenant)
class TenantAdmin(ModelAdmin):
    list_display = ["razao_social", "subdominio", "cnpj", "plano", "ativo"]
    list_filter = ["plano", "ativo"]
    search_fields = ["razao_social", "nome_fantasia", "cnpj", "subdominio"]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin, ModelAdmin):
    list_display = ["nome_completo", "email", "tenant", "papel", "ativo"]
    list_filter = ["papel", "ativo", "tenant"]
    search_fields = ["nome_completo", "email", "creci"]
    ordering = ["nome_completo"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados", {"fields": ("nome_completo", "telefone", "creci", "avatar")}),
        ("Vínculo", {"fields": ("tenant", "papel")}),
        (
            "Permissões",
            {"fields": ("ativo", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Datas", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nome_completo",
                    "tenant",
                    "papel",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
