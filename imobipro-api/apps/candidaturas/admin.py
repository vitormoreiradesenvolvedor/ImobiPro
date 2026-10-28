from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.candidaturas.models import Candidatura, DocumentoCandidatura, EventoCandidatura


class DocumentoInline(TabularInline):
    model = DocumentoCandidatura
    extra = 0
    raw_id_fields = ["conferido_por"]


class EventoInline(TabularInline):
    model = EventoCandidatura
    extra = 0
    raw_id_fields = ["usuario"]


@admin.register(Candidatura)
class CandidaturaAdmin(ModelAdmin):
    list_display = [
        "protocolo",
        "pretendente_nome",
        "imovel",
        "status",
        "analista",
        "criado_em",
    ]
    list_filter = ["status", "tenant", "criado_em"]
    search_fields = [
        "protocolo",
        "pretendente_nome",
        "pretendente_cpf",
        "pretendente_email",
    ]
    # O token é a chave do link público de envio de documentos: só leitura.
    readonly_fields = ["protocolo", "token", "decidido_em"]
    raw_id_fields = ["imovel", "ticket", "analista", "pessoa", "contrato"]
    date_hierarchy = "criado_em"
    inlines = [DocumentoInline, EventoInline]


@admin.register(DocumentoCandidatura)
class DocumentoCandidaturaAdmin(ModelAdmin):
    list_display = ["candidatura", "tipo", "status", "conferido_por", "conferido_em"]
    list_filter = ["tipo", "status"]
    search_fields = ["candidatura__protocolo", "nome_original"]
    raw_id_fields = ["candidatura", "conferido_por"]


@admin.register(EventoCandidatura)
class EventoCandidaturaAdmin(ModelAdmin):
    list_display = [
        "candidatura",
        "descricao",
        "usuario",
        "visivel_ao_cliente",
        "criado_em",
    ]
    list_filter = ["visivel_ao_cliente", "criado_em"]
    search_fields = ["descricao", "candidatura__protocolo"]
    raw_id_fields = ["candidatura", "usuario"]
