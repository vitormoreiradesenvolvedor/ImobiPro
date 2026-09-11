from django.contrib import admin

from unfold.admin import ModelAdmin, TabularInline

from apps.imoveis.models import Caracteristica, FotoImovel, HistoricoImovel, Imovel


class FotoInline(TabularInline):
    model = FotoImovel
    extra = 0
    fields = ["arquivo", "legenda", "ordem", "capa"]


@admin.register(Imovel)
class ImovelAdmin(ModelAdmin):
    list_display = [
        "codigo",
        "titulo",
        "tipo",
        "finalidade",
        "situacao",
        "valor_venda",
        "valor_locacao",
        "publicado_site",
    ]
    list_filter = ["situacao", "finalidade", "tipo", "publicado_site", "tenant"]
    search_fields = ["codigo", "titulo", "matricula"]
    raw_id_fields = ["proprietario", "endereco", "captador"]
    filter_horizontal = ["caracteristicas"]
    inlines = [FotoInline]
    readonly_fields = ["codigo", "visualizacoes", "busca"]


@admin.register(Caracteristica)
class CaracteristicaAdmin(ModelAdmin):
    list_display = ["nome", "slug", "grupo"]
    prepopulated_fields = {"slug": ["nome"]}


@admin.register(HistoricoImovel)
class HistoricoImovelAdmin(ModelAdmin):
    list_display = ["imovel", "tipo", "descricao", "criado_em"]
    list_filter = ["tipo"]
