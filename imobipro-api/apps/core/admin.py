from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.core.models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(ModelAdmin):
    """Trilha de auditoria: consulta apenas, ninguém edita o histórico."""

    list_display = ["criado_em", "acao", "modelo", "objeto_id", "usuario", "ip"]
    list_filter = ["acao", "modelo", "tenant", "criado_em"]
    search_fields = ["modelo", "objeto_id", "usuario__email"]
    date_hierarchy = "criado_em"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
