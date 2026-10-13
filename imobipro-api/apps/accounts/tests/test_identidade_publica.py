"""A marca da imobiliária no site aberto, sem token e sem vazar cadastro."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import TenantFactory


@pytest.fixture
def cliente():
    return APIClient()


@pytest.mark.django_db
def test_devolve_a_marca_da_imobiliaria(cliente):
    TenantFactory(
        subdominio="vitrine",
        nome_fantasia="Imobiliária Central",
        cor_primaria="#123456",
        creci="MG-1234-J",
        telefone="3599990000",
    )

    resposta = cliente.get("/api/v1/public/vitrine/identidade/")

    assert resposta.status_code == 200
    assert resposta.data["nome"] == "Imobiliária Central"
    assert resposta.data["cor_primaria"] == "#123456"
    assert resposta.data["creci"] == "MG-1234-J"


@pytest.mark.django_db
def test_sem_nome_fantasia_usa_a_razao_social(cliente):
    TenantFactory(
        subdominio="sofantasia", nome_fantasia="", razao_social="Duarte Imóveis Ltda"
    )

    resposta = cliente.get("/api/v1/public/sofantasia/identidade/")

    assert resposta.data["nome"] == "Duarte Imóveis Ltda"


@pytest.mark.django_db
def test_nao_expoe_cadastro_da_assinante(cliente):
    TenantFactory(subdominio="discreta", cnpj="99999999000199")

    resposta = cliente.get("/api/v1/public/discreta/identidade/")

    assert "cnpj" not in resposta.data
    assert "plano" not in resposta.data
    assert "id" not in resposta.data


@pytest.mark.django_db
def test_imobiliaria_inativa_nao_tem_site(cliente):
    TenantFactory(subdominio="cancelada", ativo=False)

    assert cliente.get("/api/v1/public/cancelada/identidade/").status_code == 404


@pytest.mark.django_db
def test_subdominio_inexistente_da_404(cliente):
    assert cliente.get("/api/v1/public/nao-existe/identidade/").status_code == 404
