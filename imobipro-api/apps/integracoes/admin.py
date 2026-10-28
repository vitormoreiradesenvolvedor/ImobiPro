from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.integracoes.models import EventoIntegracao, IntegracaoPortal


@admin.register(IntegracaoPortal)
class IntegracaoPortalAdmin(ModelAdmin):
    list_display = ["tenant", "portal", "ativo", "ultima_sincronizacao", "total_publicados"]
    list_filter = ["portal", "ativo"]
    readonly_fields = ["segredo_webhook"]


@admin.register(EventoIntegracao)
class EventoIntegracaoAdmin(ModelAdmin):
    list_display = ["evento", "portal", "direcao", "status", "tentativas", "criado_em"]
    list_filter = ["status", "direcao", "portal"]
    search_fields = ["referencia"]
