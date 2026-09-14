"""Formulário do site: vira lead, distribui e notifica sem autenticação."""

import pytest
from django.urls import reverse

from apps.crm.models import Lead, OrigemLead
from apps.imoveis.services import publicar
from apps.notificacoes.models import Notificacao

pytestmark = pytest.mark.django_db


def url(tenant):
    return reverse("contato-publico", kwargs={"subdominio": tenant.subdominio})


def test_contato_do_site_cria_lead_e_distribui(api, tenant, corretor):
    resposta = api.post(
        url(tenant),
        {
            "nome": "Visitante",
            "email": "visitante@cliente.test",
            "mensagem": "Tenho interesse.",
        },
        format="json",
    )

    assert resposta.status_code == 201
    lead = Lead.objects.get(tenant=tenant)
    assert lead.origem == OrigemLead.SITE
    assert lead.corretor_id == corretor.id
    assert Notificacao.objects.filter(usuario=corretor, tipo="LEAD_NOVO").exists()


def test_contato_vincula_o_imovel_pelo_codigo(api, tenant, corretor, imovel_publicavel):
    publicar(imovel_publicavel)

    api.post(
        url(tenant),
        {
            "nome": "Visitante",
            "telefone": "35990001111",
            "imovel_codigo": imovel_publicavel.codigo,
        },
        format="json",
    )

    assert Lead.objects.get(tenant=tenant).imovel_interesse_id == imovel_publicavel.pk


def test_contato_exige_email_ou_telefone(api, tenant):
    resposta = api.post(url(tenant), {"nome": "Anônimo"}, format="json")

    assert resposta.status_code == 400


def test_contato_em_subdominio_inexistente_retorna_404(api):
    resposta = api.post(
        reverse("contato-publico", kwargs={"subdominio": "nao-existe"}),
        {"nome": "X", "email": "x@y.test"},
        format="json",
    )

    assert resposta.status_code == 404


def test_resposta_nao_vaza_dado_do_lead(api, tenant, corretor):
    resposta = api.post(
        url(tenant), {"nome": "Visitante", "email": "v@cliente.test"}, format="json"
    )

    assert not resposta.data


def test_imovel_nao_publicado_nao_e_vinculado(api, tenant, corretor, imovel):
    api.post(
        url(tenant),
        {"nome": "Visitante", "email": "v@cliente.test", "imovel_codigo": imovel.codigo},
        format="json",
    )

    assert Lead.objects.get(tenant=tenant).imovel_interesse_id is None
