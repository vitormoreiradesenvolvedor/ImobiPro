"""Prova de que nenhum tenant enxerga dado de outro.

Este arquivo é o gate do risco nº 1 do handoff. Toda ViewSet nova entra aqui.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import Papel
from apps.accounts.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_listagem_de_usuarios_so_mostra_o_proprio_tenant(
    api, admin_imobiliaria, outro_tenant
):
    intruso = UsuarioFactory(tenant=outro_tenant, papel=Papel.CORRETOR)
    api.force_authenticate(user=admin_imobiliaria)

    resposta = api.get(reverse("usuario-list"))
    emails = [item["email"] for item in resposta.data["results"]]

    assert admin_imobiliaria.email in emails
    assert intruso.email not in emails


def test_detalhe_de_usuario_de_outro_tenant_retorna_404(
    api, admin_imobiliaria, outro_tenant
):
    intruso = UsuarioFactory(tenant=outro_tenant)
    api.force_authenticate(user=admin_imobiliaria)

    resposta = api.get(reverse("usuario-detail", args=[intruso.pk]))

    # 404 e não 403: o recurso não deve nem confirmar que existe.
    assert resposta.status_code == 404


def test_edicao_de_usuario_de_outro_tenant_retorna_404(
    api, admin_imobiliaria, outro_tenant
):
    intruso = UsuarioFactory(tenant=outro_tenant, nome_completo="Alvo")
    api.force_authenticate(user=admin_imobiliaria)

    resposta = api.patch(
        reverse("usuario-detail", args=[intruso.pk]),
        {"nome_completo": "Sequestrado"},
        format="json",
    )

    assert resposta.status_code == 404
    intruso.refresh_from_db()
    assert intruso.nome_completo == "Alvo"


def test_superadmin_enxerga_todos_os_tenants(api, admin_imobiliaria, outro_tenant):
    de_fora = UsuarioFactory(tenant=outro_tenant)
    superadmin = UsuarioFactory(tenant=None, papel=Papel.SUPERADMIN)
    api.force_authenticate(user=superadmin)

    resposta = api.get(reverse("usuario-list"))
    emails = [item["email"] for item in resposta.data["results"]]

    assert de_fora.email in emails
    assert admin_imobiliaria.email in emails


def test_corretor_nao_cria_usuario(api, corretor):
    api.force_authenticate(user=corretor)

    resposta = api.post(
        reverse("usuario-list"),
        {
            "email": "x@imobipro.test",
            "nome_completo": "X",
            "papel": Papel.CORRETOR,
            "senha": "senha-forte-1234",
        },
        format="json",
    )

    assert resposta.status_code == 403


def test_listagem_de_usuarios_nao_dispara_n_mais_um(api, admin_imobiliaria):
    """Listar N usuários custa 2 consultas, não 2 + N.

    SAVEPOINT/RELEASE do ATOMIC_REQUESTS são descartados: eles medem transação,
    não acesso a dado. O que interessa é que o número de SELECTs não cresça com
    a quantidade de linhas é isso que o select_related('tenant') garante.
    """

    UsuarioFactory.create_batch(5, tenant=admin_imobiliaria.tenant)
    api.force_authenticate(user=admin_imobiliaria)

    with CaptureQueriesContext(connection) as consultas:
        api.get(reverse("usuario-list"))

    selects = [
        c["sql"] for c in consultas.captured_queries if c["sql"].startswith("SELECT")
    ]

    assert len(selects) == 2, selects  # COUNT da paginação + página com JOIN
    assert "INNER JOIN" in selects[1]
