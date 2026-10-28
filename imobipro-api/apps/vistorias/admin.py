from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.vistorias.models import FotoItemVistoria, ItemVistoria, Vistoria


class ItemInline(TabularInline):
    model = ItemVistoria
    extra = 0


class FotoItemInline(TabularInline):
    model = FotoItemVistoria
    extra = 0


@admin.register(Vistoria)
class VistoriaAdmin(ModelAdmin):
    list_display = ["contrato", "tipo", "status", "realizada_em", "vistoriador"]
    list_filter = ["tipo", "status", "tenant"]
    raw_id_fields = ["contrato", "vistoriador"]
    inlines = [ItemInline]


# Inline não aninha no admin: as fotos de cada item ficam na tela do item.
@admin.register(ItemVistoria)
class ItemVistoriaAdmin(ModelAdmin):
    list_display = ["vistoria", "comodo", "item", "estado", "ordem"]
    list_filter = ["estado", "comodo"]
    search_fields = ["comodo", "item", "observacao"]
    raw_id_fields = ["vistoria"]
    inlines = [FotoItemInline]
