from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.locacao.models import Cobranca, EventoCobranca, Repasse


@admin.register(Cobranca)
class CobrancaAdmin(ModelAdmin):
    list_display = [
        "contrato",
        "competencia",
        "vencimento",
        "valor_total",
        "status",
        "pago_em",
    ]
    list_filter = ["status", "tenant"]
    search_fields = ["contrato__numero"]
    raw_id_fields = ["contrato"]


@admin.register(Repasse)
class RepasseAdmin(ModelAdmin):
    list_display = [
        "contrato",
        "competencia",
        "valor_bruto",
        "taxa_administracao",
        "valor_liquido",
        "status",
    ]
    list_filter = ["status"]
    raw_id_fields = ["contrato", "cobranca"]


@admin.register(EventoCobranca)
class EventoCobrancaAdmin(ModelAdmin):
    list_display = ["cobranca", "etapa", "canal", "criado_em"]
    list_filter = ["etapa", "canal"]
