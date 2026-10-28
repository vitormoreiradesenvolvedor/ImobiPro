from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.atendimento.models import EventoTicket, Ticket


class EventoInline(TabularInline):
    model = EventoTicket
    extra = 0
    raw_id_fields = ["usuario"]


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = [
        "protocolo",
        "tipo",
        "status",
        "solicitante_nome",
        "analista",
        "criado_em",
    ]
    list_filter = ["tipo", "status", "preferencia_periodo", "tenant", "criado_em"]
    search_fields = [
        "protocolo",
        "solicitante_nome",
        "solicitante_email",
        "solicitante_telefone",
    ]
    readonly_fields = ["protocolo", "primeira_resposta_em", "encerrado_em"]
    raw_id_fields = ["imovel", "lead", "analista"]
    date_hierarchy = "criado_em"
    inlines = [EventoInline]


@admin.register(EventoTicket)
class EventoTicketAdmin(ModelAdmin):
    list_display = ["ticket", "descricao", "usuario", "visivel_ao_cliente", "criado_em"]
    list_filter = ["visivel_ao_cliente", "criado_em"]
    search_fields = ["descricao", "ticket__protocolo"]
    raw_id_fields = ["ticket", "usuario"]
