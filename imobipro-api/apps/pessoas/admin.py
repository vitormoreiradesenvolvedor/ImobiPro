from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.pessoas.models import Endereco, Pessoa


@admin.register(Pessoa)
class PessoaAdmin(ModelAdmin):
    list_display = ["nome", "cpf_cnpj", "tipo", "telefone", "tenant"]
    list_filter = ["tipo", "tenant"]
    search_fields = ["nome", "cpf_cnpj", "email"]
    raw_id_fields = ["endereco"]


@admin.register(Endereco)
class EnderecoAdmin(ModelAdmin):
    list_display = ["logradouro", "numero", "bairro", "cidade", "uf"]
    list_filter = ["uf", "cidade"]
    search_fields = ["logradouro", "bairro", "cidade", "cep"]
