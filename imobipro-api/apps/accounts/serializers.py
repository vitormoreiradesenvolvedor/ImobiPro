import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Papel, Tenant

Usuario = get_user_model()


class TenantSerializer(serializers.ModelSerializer):
    plano_display = serializers.CharField(source="get_plano_display", read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "razao_social",
            "nome_fantasia",
            "cnpj",
            "creci",
            "subdominio",
            "plano",
            "plano_display",
            "ativo",
            "logo",
            "cor_primaria",
            "telefone",
            "email_contato",
        ]
        read_only_fields = ["id", "plano", "ativo"]


class UsuarioSerializer(serializers.ModelSerializer):
    papel_display = serializers.CharField(source="get_papel_display", read_only=True)

    class Meta:
        model = Usuario
        # Campos explícitos: nunca `__all__`, para não vazar hash de senha,
        # flags de permissão ou o tenant de outra imobiliária.
        fields = [
            "id",
            "email",
            "nome_completo",
            "telefone",
            "creci",
            "papel",
            "papel_display",
            "avatar",
            "ativo",
            "last_login",
            "criado_em",
        ]
        read_only_fields = ["id", "last_login", "criado_em"]


class UsuarioCriacaoSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(write_only=True, min_length=10, source="password")

    class Meta:
        model = Usuario
        fields = ["id", "email", "nome_completo", "telefone", "creci", "papel", "senha"]

    def validate_papel(self, valor):
        if valor == Papel.SUPERADMIN:
            raise serializers.ValidationError(
                "Papel SUPERADMIN não pode ser atribuído pela API."
            )
        return valor

    def create(self, validated_data):
        senha = validated_data.pop("password")
        return Usuario.objects.create_user(password=senha, **validated_data)


class PerfilSerializer(serializers.ModelSerializer):
    """Payload de /auth/me/: usuário + tenant + capacidades do papel."""

    papel_display = serializers.CharField(source="get_papel_display", read_only=True)
    tenant = TenantSerializer(read_only=True)
    permissoes = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "email",
            "nome_completo",
            "telefone",
            "creci",
            "papel",
            "papel_display",
            "avatar",
            "tenant",
            "permissoes",
        ]

    @extend_schema_field(serializers.DictField(child=serializers.BooleanField()))
    def get_permissoes(self, usuario):
        papel = usuario.papel
        return {
            "ver_financeiro": papel in {Papel.ADMIN, Papel.FINANCEIRO, Papel.SUPERADMIN},
            "ver_crm": papel in {Papel.ADMIN, Papel.GERENTE, Papel.CORRETOR},
            "gerenciar_usuarios": papel in {Papel.ADMIN, Papel.SUPERADMIN},
            "gerenciar_equipe": papel in {Papel.ADMIN, Papel.GERENTE, Papel.SUPERADMIN},
            "ver_todos_leads": papel in {Papel.ADMIN, Papel.GERENTE, Papel.SUPERADMIN},
            # Cliente com acesso não opera o painel: ele vê o portal do contrato.
            "usar_portal": papel in {Papel.INQUILINO, Papel.PROPRIETARIO},
        }


class LoginSerializer(TokenObtainPairSerializer):
    """Token com claim de tenant e resposta já contendo o perfil."""

    @classmethod
    def get_token(cls, usuario):
        token = super().get_token(usuario)
        token["tenant_id"] = str(usuario.tenant_id) if usuario.tenant_id else None
        token["papel"] = usuario.papel
        token["nome"] = usuario.nome_completo
        return token

    def validate(self, attrs):
        dados = super().validate(attrs)

        if self.user.tenant and not self.user.tenant.ativo:
            raise serializers.ValidationError(
                {"detail": "Imobiliária inativa. Procure o administrador."}
            )

        dados["user"] = PerfilSerializer(self.user, context=self.context).data
        return dados


class CadastroSerializer(serializers.Serializer):
    """Cadastre-se: a imobiliária nova entra com o primeiro administrador.

    Quem se cadastra é sempre ADMIN do próprio tenant; os demais papéis são
    criados por ele dentro do painel, nunca pela porta pública.
    """

    razao_social = serializers.CharField(max_length=255)
    nome_fantasia = serializers.CharField(max_length=255, required=False, allow_blank=True)
    cnpj = serializers.CharField(max_length=18)
    subdominio = serializers.SlugField(max_length=63)
    nome_completo = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    telefone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    senha = serializers.CharField(write_only=True, min_length=10)

    def validate_cnpj(self, valor):
        # Aceita com ou sem máscara; grava só os dígitos, como o resto do sistema.
        digitos = re.sub(r"\D", "", valor)
        if len(digitos) != 14:
            raise serializers.ValidationError("CNPJ deve ter 14 dígitos.")
        if Tenant.objects.filter(cnpj=digitos).exists():
            raise serializers.ValidationError("Já existe uma imobiliária com este CNPJ.")
        return digitos

    def validate_subdominio(self, valor):
        valor = valor.lower()
        if Tenant.objects.filter(subdominio=valor).exists():
            raise serializers.ValidationError("Este endereço já está em uso.")
        return valor

    def validate_email(self, valor):
        valor = valor.lower()
        if Usuario.objects.filter(email__iexact=valor).exists():
            raise serializers.ValidationError("Já existe uma conta com este e-mail.")
        return valor

    def validate(self, attrs):
        # Os validadores do AUTH_PASSWORD_VALIDATORS comparam a senha com o
        # nome e o e-mail, então rodam com um usuário provisório em memória.
        provisorio = Usuario(email=attrs["email"], nome_completo=attrs["nome_completo"])
        try:
            validate_password(attrs["senha"], user=provisorio)
        except DjangoValidationError as erro:
            raise serializers.ValidationError({"senha": list(erro.messages)}) from erro
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        tenant = Tenant.objects.create(
            razao_social=validated_data["razao_social"],
            nome_fantasia=validated_data.get("nome_fantasia", ""),
            cnpj=validated_data["cnpj"],
            subdominio=validated_data["subdominio"],
            telefone=validated_data.get("telefone", ""),
            email_contato=validated_data["email"],
        )
        return Usuario.objects.create_user(
            email=validated_data["email"],
            password=validated_data["senha"],
            nome_completo=validated_data["nome_completo"],
            telefone=validated_data.get("telefone", ""),
            papel=Papel.ADMIN,
            tenant=tenant,
        )


class SolicitacaoResetSenhaSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmacaoResetSenhaSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    nova_senha = serializers.CharField(min_length=10)


class IdentidadePublicaSerializer(serializers.ModelSerializer):
    """O que o site público pode saber da imobiliária: marca, não cadastro.

    Fica de fora tudo que identifica a empresa como assinante (CNPJ, plano,
    situação): a vitrine é aberta, e um endpoint sem token não devolve nada
    além do que já estaria impresso na fachada.
    """

    nome = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            "nome",
            "subdominio",
            "logo",
            "cor_primaria",
            "creci",
            "telefone",
            "email_contato",
        ]

    def get_nome(self, tenant) -> str:
        return tenant.nome_fantasia or tenant.razao_social
