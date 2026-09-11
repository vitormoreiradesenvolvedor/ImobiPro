from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.validators import validar_cep, validar_cpf_cnpj
from apps.pessoas.models import Endereco, Pessoa


class EnderecoSerializer(serializers.ModelSerializer):
    resumo = serializers.CharField(read_only=True)
    geocodificado = serializers.BooleanField(read_only=True)
    # O front manda "37200-000"; o banco guarda só dígitos. O limite maior aqui
    # deixa a máscara passar para ser normalizada em `validate_cep`.
    cep = serializers.CharField(max_length=9, required=False, allow_blank=True)

    class Meta:
        model = Endereco
        fields = [
            "id",
            "cep",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "uf",
            "latitude",
            "longitude",
            "resumo",
            "geocodificado",
        ]
        read_only_fields = ["id"]

    def validate_cep(self, valor):
        try:
            return validar_cep(valor)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(erro.messages) from erro


class PessoaSerializer(serializers.ModelSerializer):
    endereco = EnderecoSerializer(required=False, allow_null=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    # Aceita "12.345.678/0001-99" (18 caracteres) e normaliza para dígitos.
    cpf_cnpj = serializers.CharField(max_length=18)

    class Meta:
        model = Pessoa
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "nome",
            "foto",
            "cpf_cnpj",
            "rg_ie",
            "data_nascimento",
            "estado_civil",
            "profissao",
            "renda_mensal",
            "email",
            "telefone",
            "whatsapp",
            "endereco",
            "dados_bancarios",
            "observacoes",
            "criado_em",
        ]
        read_only_fields = ["id", "criado_em"]

    def validate_cpf_cnpj(self, valor):
        try:
            documento = validar_cpf_cnpj(valor)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(erro.messages) from erro

        tenant = self.context["request"].user.tenant
        existente = Pessoa.objects.filter(
            tenant=tenant, cpf_cnpj=documento, deletado_em__isnull=True
        )
        if self.instance:
            existente = existente.exclude(pk=self.instance.pk)
        if existente.exists():
            raise serializers.ValidationError("Já existe uma pessoa com este documento.")

        return documento

    def validate(self, attrs):
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        documento = attrs.get("cpf_cnpj", getattr(self.instance, "cpf_cnpj", ""))

        if tipo == "JURIDICA" and len(documento) == 11:
            raise serializers.ValidationError({"cpf_cnpj": "Pessoa jurídica exige CNPJ."})
        if tipo == "FISICA" and len(documento) == 14:
            raise serializers.ValidationError({"cpf_cnpj": "Pessoa física exige CPF."})

        return attrs

    def create(self, validated_data):
        dados_endereco = validated_data.pop("endereco", None)
        if dados_endereco:
            validated_data["endereco"] = Endereco.objects.create(**dados_endereco)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        dados_endereco = validated_data.pop("endereco", None)

        if dados_endereco is not None:
            if instance.endereco:
                for campo, valor in dados_endereco.items():
                    setattr(instance.endereco, campo, valor)
                instance.endereco.save()
            else:
                instance.endereco = Endereco.objects.create(**dados_endereco)

        return super().update(instance, validated_data)


class PessoaResumoSerializer(serializers.ModelSerializer):
    """Usado dentro de imóvel, contrato e lead não carrega o cadastro inteiro."""

    class Meta:
        model = Pessoa
        fields = ["id", "nome", "cpf_cnpj", "telefone", "email"]


class ConsultaCepSerializer(serializers.Serializer):
    cep = serializers.CharField(read_only=True)
    logradouro = serializers.CharField(read_only=True)
    bairro = serializers.CharField(read_only=True)
    cidade = serializers.CharField(read_only=True)
    uf = serializers.CharField(read_only=True)
