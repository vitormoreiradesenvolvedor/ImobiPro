import pytest
from django.conf import settings
from django.urls import reverse

from apps.accounts.models import Papel, Tenant, Usuario
from apps.accounts.tests.factories import TenantFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

DADOS = {
    "razao_social": "Serra Verde Imóveis Ltda",
    "nome_fantasia": "Serra Verde",
    "cnpj": "12.345.678/0001-90",
    "subdominio": "serra-verde",
    "nome_completo": "Marina Costa",
    "email": "Marina@SerraVerde.com.br",
    "telefone": "35999990000",
    "senha": "casa-nova-2026!",
}


def cadastrar(api, **mudancas):
    return api.post(reverse("cadastro"), {**DADOS, **mudancas}, format="json")


def test_cadastro_cria_imobiliaria_e_administrador(api):
    resposta = cadastrar(api)

    assert resposta.status_code == 201
    tenant = Tenant.objects.get(subdominio="serra-verde")
    assert tenant.cnpj == "12345678000190"
    usuario = Usuario.objects.get(email="marina@serraverde.com.br")
    assert usuario.tenant == tenant
    assert usuario.papel == Papel.ADMIN
    assert usuario.check_password(DADOS["senha"])


def test_cadastro_ja_abre_sessao_como_o_login(api):
    resposta = cadastrar(api)

    assert "access" in resposta.data
    assert "refresh" not in resposta.data
    assert resposta.data["user"]["papel"] == Papel.ADMIN
    assert resposta.data["user"]["permissoes"]["gerenciar_usuarios"] is True
    assert resposta.cookies[settings.REFRESH_COOKIE_NAME]["httponly"] is True


def test_conta_criada_consegue_entrar_depois(api):
    cadastrar(api)

    resposta = api.post(
        reverse("login"),
        {"email": "marina@serraverde.com.br", "password": DADOS["senha"]},
        format="json",
    )
    assert resposta.status_code == 200


def test_cadastro_ignora_papel_enviado_pelo_cliente(api):
    cadastrar(api, papel=Papel.SUPERADMIN)

    assert Usuario.objects.get(email="marina@serraverde.com.br").papel == Papel.ADMIN


def test_cadastro_recusa_email_ja_usado(api):
    UsuarioFactory(email="marina@serraverde.com.br")

    resposta = cadastrar(api)

    assert resposta.status_code == 400
    assert "email" in resposta.data["campos"]
    assert not Tenant.objects.filter(subdominio="serra-verde").exists()


def test_cadastro_recusa_cnpj_e_subdominio_repetidos(api):
    TenantFactory(cnpj="12345678000190", subdominio="serra-verde")

    resposta = cadastrar(api)

    assert resposta.status_code == 400
    assert {"cnpj", "subdominio"} <= set(resposta.data["campos"])


def test_cadastro_recusa_cnpj_incompleto(api):
    resposta = cadastrar(api, cnpj="123")

    assert resposta.status_code == 400
    assert "cnpj" in resposta.data["campos"]


def test_cadastro_recusa_senha_fraca(api):
    resposta = cadastrar(api, senha="1234567890")

    assert resposta.status_code == 400
    assert "senha" in resposta.data["campos"]
    assert not Usuario.objects.filter(email="marina@serraverde.com.br").exists()
