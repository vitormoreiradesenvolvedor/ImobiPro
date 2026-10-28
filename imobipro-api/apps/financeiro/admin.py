from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.financeiro.models import Transacao


@admin.register(Transacao)
class TransacaoAdmin(ModelAdmin):
    list_display = ["data_competencia", "tipo", "categoria", "descricao", "valor"]
    list_filter = ["tipo", "categoria", "tenant"]
    search_fields = ["descricao"]
    raw_id_fields = ["cobranca", "repasse", "comissao", "contrato", "estorno_de"]

    def has_delete_permission(self, request, obj=None):
        # Transação não se apaga nem pelo admin: estorna.
        return False
