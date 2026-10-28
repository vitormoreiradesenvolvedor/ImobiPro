from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.crm.models import Interacao, Lead, Proposta, Visita


class InteracaoInline(TabularInline):
    model = Interacao
    extra = 0
    readonly_fields = ["tipo", "descricao", "usuario", "criado_em"]
    can_delete = False


@admin.register(Lead)
class LeadAdmin(ModelAdmin):
    list_display = ["nome", "origem", "estagio", "corretor", "sla_cumprido", "criado_em"]
    list_filter = ["estagio", "origem", "temperatura", "sla_cumprido", "tenant"]
    search_fields = ["nome", "email", "telefone"]
    raw_id_fields = ["imovel_interesse", "corretor"]
    inlines = [InteracaoInline]


@admin.register(Visita)
class VisitaAdmin(ModelAdmin):
    list_display = ["lead", "imovel", "agendada_para", "realizada", "cancelada"]
    list_filter = ["realizada", "cancelada"]
    raw_id_fields = ["lead", "imovel", "corretor"]


@admin.register(Proposta)
class PropostaAdmin(ModelAdmin):
    list_display = ["imovel", "lead", "valor_ofertado", "status", "validade"]
    list_filter = ["status"]
    raw_id_fields = ["lead", "imovel", "criada_por"]
