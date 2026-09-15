from django.contrib import admin

from unfold.admin import ModelAdmin, TabularInline

from apps.vistorias.models import ItemVistoria, Vistoria


class ItemInline(TabularInline):
    model = ItemVistoria
    extra = 0


@admin.register(Vistoria)
class VistoriaAdmin(ModelAdmin):
    list_display = ["contrato", "tipo", "status", "realizada_em", "vistoriador"]
    list_filter = ["tipo", "status", "tenant"]
    raw_id_fields = ["contrato", "vistoriador"]
    inlines = [ItemInline]
