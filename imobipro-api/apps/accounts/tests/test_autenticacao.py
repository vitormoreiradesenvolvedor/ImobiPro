import pytest
from django.conf import settings
from django.urls import reverse

from apps.accounts.models import Papel
from apps.accounts.tests.factories import UsuarioFactory

SENHA = "senha-de-teste-123"

pytestmark = pytest.mark.django_db


def test_login_retorna_access_e_perfil(api, corretor):
    resposta = api.post(
        reverse("login"), {"email": corretor.email, "password": SENHA}, format="json"
    )

    assert resposta.status_code == 200
    assert "access" in resposta.data
    assert resposta.data["user"]["email"] == corretor.email
    assert resposta.data["user"]["tenant"]["id"] == str(corretor.tenant_id)


def test_login_nao_devolve_refresh_no_corpo_e_grava_cookie_httponly(api, corretor):
    resposta = api.post(
        reverse("login"), {"email": corretor.email, "password": SENHA}, format="json"
    )

    assert "refresh" not in resposta.data
    cookie = resposta.cookies[settings.REFRESH_COOKIE_NAME]
    assert cookie["httponly"] is True
    assert cookie["path"] == settings.REFRESH_COOKIE_PATH


def test_login_com_senha_errada_falha(api, corretor):
    resposta = api.post(
        reverse("login"), {"email": corretor.email, "password": "errada"}, format="json"
    )
    assert resposta.status_code == 401


def test_login_de_usuario_inativo_falha(api, corretor):
    corretor.ativo = False
    corretor.save(update_fields=["ativo"])

    resposta = api.post(
        reverse("login"), {"email": corretor.email, "password": SENHA}, format="json"
    )
    assert resposta.status_code == 401


def test_login_com_tenant_inativo_falha(api, corretor):
    corretor.tenant.ativo = False
    corretor.tenant.save(update_fields=["ativo"])

    resposta = api.post(
        reverse("login"), {"email": corretor.email, "password": SENHA}, format="json"
    )
    assert resposta.status_code == 400


def test_token_carrega_claim_de_tenant(api, corretor):
    from rest_framework_simplejwt.tokens import AccessToken

    resposta = api.post(
        reverse("login"), {"email": corretor.email, "password": SENHA}, format="json"
    )
    token = AccessToken(resposta.data["access"])

    assert token["tenant_id"] == str(corretor.tenant_id)
    assert token["papel"] == Papel.CORRETOR


def test_refresh_usa_cookie_e_renova_access(api, corretor):
    api.post(reverse("login"), {"email": corretor.email, "password": SENHA}, format="json")

    resposta = api.post(reverse("refresh"))

    assert resposta.status_code == 200
    assert "access" in resposta.data


def test_refresh_sem_cookie_retorna_401(api):
    resposta = api.post(reverse("refresh"))
    assert resposta.status_code == 401
    assert resposta.data["code"] == "sem_refresh"


def test_logout_invalida_refresh(api, corretor):
    api.post(reverse("login"), {"email": corretor.email, "password": SENHA}, format="json")
    api.force_authenticate(user=corretor)

    assert api.post(reverse("logout")).status_code == 204
    assert api.post(reverse("refresh")).status_code == 401


def test_me_exige_autenticacao(api):
    assert api.get(reverse("me")).status_code == 401


def test_me_devolve_permissoes_do_papel(api, corretor):
    api.force_authenticate(user=corretor)
    resposta = api.get(reverse("me"))

    assert resposta.data["permissoes"]["ver_crm"] is True
    assert resposta.data["permissoes"]["ver_financeiro"] is False


def test_reset_de_senha_nao_enumera_usuarios(api, corretor):
    existente = api.post(
        reverse("password-reset"), {"email": corretor.email}, format="json"
    )
    inexistente = api.post(
        reverse("password-reset"), {"email": "ninguem@imobipro.test"}, format="json"
    )

    assert existente.status_code == inexistente.status_code == 202


def test_reset_de_senha_troca_a_senha(api, corretor):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    payload = {
        "uid": urlsafe_base64_encode(force_bytes(corretor.pk)),
        "token": default_token_generator.make_token(corretor),
        "nova_senha": "nova-senha-forte-42",
    }
    assert (
        api.post(reverse("password-reset-confirmar"), payload, format="json").status_code
        == 204
    )

    corretor.refresh_from_db()
    assert corretor.check_password("nova-senha-forte-42")


def test_papel_superadmin_nao_pode_ser_criado_pela_api(api, admin_imobiliaria):
    api.force_authenticate(user=admin_imobiliaria)

    resposta = api.post(
        reverse("usuario-list"),
        {
            "email": "invasor@imobipro.test",
            "nome_completo": "Invasor",
            "papel": Papel.SUPERADMIN,
            "senha": "senha-forte-1234",
        },
        format="json",
    )

    assert resposta.status_code == 400
    assert "papel" in resposta.data["campos"]


def test_usuario_criado_herda_o_tenant_de_quem_criou(api, admin_imobiliaria):
    api.force_authenticate(user=admin_imobiliaria)

    resposta = api.post(
        reverse("usuario-list"),
        {
            "email": "novo@imobipro.test",
            "nome_completo": "Novo Corretor",
            "papel": Papel.CORRETOR,
            "senha": "senha-forte-1234",
        },
        format="json",
    )

    assert resposta.status_code == 201
    novo = UsuarioFactory._meta.model.objects.get(email="novo@imobipro.test")
    assert novo.tenant_id == admin_imobiliaria.tenant_id


# ------------------------------------------------------- limites por endpoint


def test_login_nao_divide_balde_com_a_navegacao_anonima():
    """Vitrine cheia não pode impedir a equipe de entrar no sistema.

    O balde anônimo é global e compartilhado por todo visitante. Enquanto o
    login também passava por ele, um pico no site público (ou uma bateria de
    testes) deixava a imobiliária trancada para fora do próprio sistema.
    """

    from rest_framework.throttling import ScopedRateThrottle

    from apps.accounts.views import LoginView

    classes = [type(t) for t in LoginView().get_throttles()]

    assert classes == [ScopedRateThrottle]
    assert LoginView.throttle_scope == "login"


def test_renovacao_de_sessao_tem_balde_proprio(settings):
    """Sair e entrar de novo é rotina: o refresh não divide limite com ninguém."""

    from rest_framework.throttling import ScopedRateThrottle

    from apps.accounts.views import RefreshView

    classes = [type(t) for t in RefreshView().get_throttles()]

    assert classes == [ScopedRateThrottle]
    assert RefreshView.throttle_scope == "refresh"
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["refresh"]


def test_recuperacao_de_senha_tambem_fica_fora_do_balde_anonimo():
    from rest_framework.throttling import ScopedRateThrottle

    from apps.accounts.views import ConfirmarResetSenhaView, SolicitarResetSenhaView

    for vista in [SolicitarResetSenhaView, ConfirmarResetSenhaView]:
        assert [type(t) for t in vista().get_throttles()] == [ScopedRateThrottle]


def test_identidade_do_limite_considera_o_proxy(settings):
    """Atrás do nginx, todo mundo chega com o IP do proxy.

    Sem contar o cabeçalho encaminhado, um único visitante consumiria o limite
    da aplicação inteira.
    """

    assert settings.REST_FRAMEWORK["NUM_PROXIES"] >= 1


def test_mensagem_de_limite_e_legivel():
    """ "Disponível em 3305 segundos" não ajuda ninguém na tela de login."""

    from rest_framework.exceptions import Throttled

    from apps.core.exceptions import exception_handler_padrao

    resposta = exception_handler_padrao(Throttled(wait=3305), {})

    assert resposta.status_code == 429
    assert resposta.data["code"] == "limite_de_requisicoes"
    assert resposta.data["detail"] == "Muitas tentativas. Tente de novo em 55 minuto(s)."

    curta = exception_handler_padrao(Throttled(wait=40), {})
    assert curta.data["detail"] == "Muitas tentativas. Tente de novo em 40 segundos."
