from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.contratos.models import (
    Comissao,
    ConfiguracaoComissao,
    Contrato,
    ParteContrato,
    Reajuste,
)


class ParteInline(TabularInline):
    model = ParteContrato
    extra = 0
    raw_id_fields = ["pessoa"]


class ReajusteInline(TabularInline):
    model = Reajuste
    extra = 0
    readonly_fields = [
        "data_aplicacao",
        "indice",
        "percentual",
        "valor_anterior",
        "valor_novo",
    ]


@admin.register(Contrato)
class ContratoAdmin(ModelAdmin):
    list_display = [
        "numero",
        "tipo",
        "imovel",
        "valor",
        "status",
        "data_inicio",
        "data_fim",
    ]
    list_filter = ["tipo", "status", "tenant"]
    search_fields = ["numero", "imovel__codigo"]
    raw_id_fields = ["imovel", "proposta"]
    readonly_fields = ["numero", "multa_rescisao_calculada"]
    inlines = [ParteInline, ReajusteInline]


@admin.register(Comissao)
class ComissaoAdmin(ModelAdmin):
    list_display = ["contrato", "papel", "usuario", "valor", "status"]
    list_filter = ["status", "papel"]


@admin.register(ConfiguracaoComissao)
class ConfiguracaoComissaoAdmin(ModelAdmin):
    list_display = [
        "tenant",
        "percentual_venda",
        "rateio_captador",
        "rateio_vendedor",
        "rateio_imobiliaria",
    ]
    list_filter = ["tenant"]
