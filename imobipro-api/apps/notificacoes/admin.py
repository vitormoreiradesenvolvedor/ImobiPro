from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.notificacoes.models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(ModelAdmin):
    list_display = ["titulo", "usuario", "tipo", "lida", "criado_em"]
    list_filter = ["tipo", "lida", "tenant", "criado_em"]
    search_fields = ["titulo", "descricao", "usuario__email"]
    raw_id_fields = ["usuario"]
