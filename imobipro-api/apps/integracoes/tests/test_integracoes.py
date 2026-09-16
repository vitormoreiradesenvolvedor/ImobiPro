import json

import pytest
from django.urls import reverse

from apps.crm.models import Lead, OrigemLead
from apps.imoveis.services import publicar
from apps.integracoes.models import EventoIntegracao, IntegracaoPortal, StatusEnvio
from apps.integracoes.services import assinar, normalizar_lead, sincronizar_portal

pytestmark = pytest.mark.django_db


@pytest.fixture
def integracao(tenant):
    return IntegracaoPortal.objects.create(
        tenant=tenant, portal="VIVA_REAL", identificador_externo="conta-123"
    )


def url_webhook(tenant, portal="VIVA_REAL"):
    return reverse(
        "webhook-lead", kwargs={"portal": portal, "subdominio": tenant.subdominio}
    )


def enviar(api, tenant, integracao, payload, assinatura=None):
    corpo = json.dumps(payload).encode()
    return api.post(
        url_webhook(tenant),
        data=corpo,
        content_type="application/json",
        HTTP_X_ASSINATURA=(
            assinatura
            if assinatura is not None
            else assinar(corpo, integracao.segredo_webhook)
        ),
    )


# ------------------------------------------------------------------ webhook


def test_webhook_assinado_cria_lead(api, tenant, integracao, corretor):
    resposta = enviar(
        api,
        tenant,
        integracao,
        {"name": "Paula Ribeiro", "phone": "35998887766", "message": "Quero visitar"},
    )

    assert resposta.status_code == 202
    lead = Lead.objects.get(tenant=tenant)
    assert lead.nome == "Paula Ribeiro"
    assert lead.origem == OrigemLead.PORTAL
    assert lead.corretor_id == corretor.id  # distribuído no round-robin


def test_webhook_sem_assinatura_e_recusado(api, tenant, integracao):
    resposta = enviar(api, tenant, integracao, {"name": "X", "phone": "1"}, assinatura="")

    assert resposta.status_code == 401
    assert not Lead.objects.exists()


def test_webhook_com_assinatura_errada_e_recusado_e_registrado(api, tenant, integracao):
    resposta = enviar(
        api, tenant, integracao, {"name": "X", "phone": "1"}, assinatura="sha256=deadbeef"
    )

    assert resposta.status_code == 401
    assert EventoIntegracao.objects.filter(
        evento="assinatura_invalida", status=StatusEnvio.DESCARTADO
    ).exists()


def test_assinatura_de_outro_segredo_nao_serve(api, tenant, integracao):
    corpo = json.dumps({"name": "X", "phone": "1"}).encode()

    resposta = api.post(
        url_webhook(tenant),
        data=corpo,
        content_type="application/json",
        HTTP_X_ASSINATURA=assinar(corpo, "segredo-de-outra-imobiliaria"),
    )

    assert resposta.status_code == 401


def test_webhook_de_portal_nao_configurado_retorna_404(api, tenant):
    resposta = api.post(
        url_webhook(tenant, "OLX"), data=b"{}", content_type="application/json"
    )

    assert resposta.status_code == 404


def test_payload_sem_contato_e_descartado(api, tenant, integracao, corretor):
    resposta = enviar(api, tenant, integracao, {"name": "Sem contato"})

    assert resposta.status_code == 400
    assert EventoIntegracao.objects.filter(evento="lead_descartado").exists()


def test_webhook_vincula_imovel_pelo_codigo(
    api, tenant, integracao, corretor, imovel_publicavel
):
    imovel = publicar(imovel_publicavel)

    enviar(
        api,
        tenant,
        integracao,
        {"name": "Paula", "phone": "35998887766", "listing_id": imovel.codigo},
    )

    assert Lead.objects.get(tenant=tenant).imovel_interesse_id == imovel.pk


def test_normalizacao_aceita_nomes_de_campo_de_portais_diferentes():
    do_zap = normalizar_lead(
        {"lead_name": "Ana", "lead_phone": "3599", "reference": "REF-1"}
    )
    da_olx = normalizar_lead({"nome": "Ana", "telefone": "3599", "codigo": "REF-1"})

    assert do_zap == da_olx


# -------------------------------------------------------------- publicação


def test_sincronizacao_enfileira_imoveis_publicados(integracao, imovel_publicavel):
    publicar(imovel_publicavel)

    enfileirados = sincronizar_portal(integracao)

    assert enfileirados == 1
    evento = EventoIntegracao.objects.get(direcao="SAIDA")
    assert evento.payload["codigo"] == imovel_publicavel.codigo
    assert evento.status == StatusEnvio.PENDENTE


def test_sincronizacao_ignora_imovel_nao_publicado(integracao, imovel):
    assert sincronizar_portal(integracao) == 0


def test_segunda_sincronizacao_envia_so_o_que_mudou(integracao, imovel_publicavel):
    publicar(imovel_publicavel)
    sincronizar_portal(integracao)

    assert sincronizar_portal(integracao) == 0


def test_evento_pode_ser_reprocessado_pelo_painel(
    api_autenticada, integracao, imovel_publicavel
):
    publicar(imovel_publicavel)
    sincronizar_portal(integracao)
    evento = EventoIntegracao.objects.get(direcao="SAIDA")
    evento.status = StatusEnvio.ERRO
    evento.save(update_fields=["status"])

    resposta = api_autenticada.post(
        reverse("evento-integracao-reprocessar", args=[evento.pk])
    )

    assert resposta.status_code == 200
    evento.refresh_from_db()
    # A task roda em modo eager nos testes e marca como enviado.
    assert evento.status == StatusEnvio.ENVIADO


def test_rotacao_de_segredo_invalida_o_anterior(api_autenticada, tenant, integracao):
    antigo = integracao.segredo_webhook

    api_autenticada.post(
        reverse("integracao-portal-rotacionar-segredo", args=[integracao.pk])
    )

    integracao.refresh_from_db()
    assert integracao.segredo_webhook != antigo


def test_corretor_nao_configura_integracao(api, corretor, tenant):
    api.force_authenticate(user=corretor)

    resposta = api.post(reverse("integracao-portal-list"), {"portal": "OLX"}, format="json")

    assert resposta.status_code == 400


def test_integracao_de_outro_tenant_nao_aparece(api_autenticada, outro_tenant):
    IntegracaoPortal.objects.create(tenant=outro_tenant, portal="ZAP")

    assert api_autenticada.get(reverse("integracao-portal-list")).data["count"] == 0
