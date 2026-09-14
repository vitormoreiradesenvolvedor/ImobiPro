from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.crm.models import EstagioLead, StatusProposta
from apps.crm.services import agendar_visita
from apps.crm.tests.factories import LeadFactory
from apps.imoveis.models import SituacaoImovel
from apps.imoveis.services import publicar

pytestmark = pytest.mark.django_db


@pytest.fixture
def lead(tenant, corretor, imovel_publicavel):
    return LeadFactory(tenant=tenant, corretor=corretor, imovel_interesse=imovel_publicavel)


@pytest.fixture
def imovel_disponivel(imovel_publicavel):
    return publicar(imovel_publicavel)


# ------------------------------------------------------------------ visitas


def test_agendar_visita_move_o_lead_no_funil(api_autenticada, lead, imovel_disponivel):
    resposta = api_autenticada.post(
        reverse("visita-list"),
        {
            "lead": str(lead.pk),
            "imovel": str(imovel_disponivel.pk),
            "agendada_para": (timezone.now() + timedelta(days=2)).isoformat(),
        },
        format="json",
    )

    assert resposta.status_code == 201
    lead.refresh_from_db()
    assert lead.estagio == EstagioLead.VISITA_AGENDADA
    assert lead.primeiro_contato_em is not None


def test_nao_agenda_visita_no_passado(lead, imovel_disponivel):
    from apps.crm.services import RegraDeNegocio

    ontem = timezone.now() - timedelta(hours=1)

    with pytest.raises(RegraDeNegocio, match="passado"):
        agendar_visita(lead, imovel_disponivel, ontem)


def test_nao_agenda_visita_em_imovel_vendido(lead, imovel_disponivel):
    from apps.crm.services import RegraDeNegocio
    from apps.imoveis.services import mudar_situacao

    mudar_situacao(imovel_disponivel, SituacaoImovel.VENDIDO)

    amanha = timezone.now() + timedelta(days=1)

    with pytest.raises(RegraDeNegocio, match="não recebe visita"):
        agendar_visita(lead, imovel_disponivel, amanha)


def test_feedback_marca_visita_como_realizada(api_autenticada, lead, imovel_disponivel):
    visita = agendar_visita(lead, imovel_disponivel, timezone.now() + timedelta(days=1))

    resposta = api_autenticada.post(
        reverse("visita-feedback", args=[visita.pk]),
        {
            "feedback": "Gostou do imóvel, achou o valor alto.",
            "interesse_pos_visita": "MEDIO",
        },
        format="json",
    )

    assert resposta.status_code == 200
    visita.refresh_from_db()
    assert visita.realizada is True
    lead.refresh_from_db()
    assert lead.estagio == EstagioLead.VISITA_REALIZADA


def test_agenda_do_dia_lista_apenas_visitas_nao_canceladas(
    api_autenticada, lead, imovel_disponivel
):
    hoje = timezone.now() + timedelta(hours=3)
    visita = agendar_visita(lead, imovel_disponivel, hoje)
    cancelada = agendar_visita(lead, imovel_disponivel, hoje + timedelta(hours=1))
    api_autenticada.post(reverse("visita-cancelar", args=[cancelada.pk]))

    # Consulta o dia da própria visita: perto da meia-noite, "hoje + 3h" cai
    # no dia seguinte e o teste passaria a depender da hora da execução.
    dia = timezone.localtime(visita.agendada_para).date()
    resposta = api_autenticada.get(reverse("visita-agenda"), {"data": dia.isoformat()})

    ids = [item["id"] for item in resposta.data]
    assert str(visita.pk) in ids
    assert str(cancelada.pk) not in ids


def test_visita_atrasada_e_sinalizada(lead, imovel_disponivel):
    visita = agendar_visita(lead, imovel_disponivel, timezone.now() + timedelta(minutes=1))
    visita.agendada_para = timezone.now() - timedelta(hours=2)
    visita.save(update_fields=["agendada_para"])

    assert visita.atrasada is True


# ----------------------------------------------------------------- propostas


def payload_proposta(lead, imovel, valor="330000.00"):
    return {
        "lead": str(lead.pk),
        "imovel": str(imovel.pk),
        "valor_ofertado": valor,
        "condicoes_pagamento": "Entrada de 30% e financiamento do saldo.",
        "validade": (timezone.localdate() + timedelta(days=7)).isoformat(),
    }


def test_proposta_move_o_lead_para_o_estagio_proposta(
    api_autenticada, lead, imovel_disponivel
):
    resposta = api_autenticada.post(
        reverse("proposta-list"), payload_proposta(lead, imovel_disponivel), format="json"
    )

    assert resposta.status_code == 201
    lead.refresh_from_db()
    assert lead.estagio == EstagioLead.PROPOSTA


def test_aceitar_proposta_reserva_o_imovel(api_autenticada, lead, imovel_disponivel):
    criada = api_autenticada.post(
        reverse("proposta-list"), payload_proposta(lead, imovel_disponivel), format="json"
    )

    resposta = api_autenticada.post(reverse("proposta-aceitar", args=[criada.data["id"]]))

    assert resposta.data["status"] == StatusProposta.ACEITA
    imovel_disponivel.refresh_from_db()
    assert imovel_disponivel.situacao == SituacaoImovel.RESERVADO
    lead.refresh_from_db()
    assert lead.estagio == EstagioLead.NEGOCIACAO


def test_aceite_recusa_as_demais_propostas_do_imovel(
    api_autenticada, lead, tenant, corretor, imovel_disponivel
):
    concorrente = LeadFactory(tenant=tenant, corretor=corretor)
    perdedora = api_autenticada.post(
        reverse("proposta-list"),
        payload_proposta(concorrente, imovel_disponivel, "300000.00"),
        format="json",
    )
    vencedora = api_autenticada.post(
        reverse("proposta-list"), payload_proposta(lead, imovel_disponivel), format="json"
    )

    api_autenticada.post(reverse("proposta-aceitar", args=[vencedora.data["id"]]))

    detalhe = api_autenticada.get(reverse("proposta-detail", args=[perdedora.data["id"]]))
    assert detalhe.data["status"] == StatusProposta.RECUSADA


def test_proposta_expirada_nao_pode_ser_aceita(api_autenticada, lead, imovel_disponivel):
    from apps.crm.models import Proposta

    criada = api_autenticada.post(
        reverse("proposta-list"), payload_proposta(lead, imovel_disponivel), format="json"
    )
    Proposta.objects.filter(pk=criada.data["id"]).update(
        validade=timezone.localdate() - timedelta(days=1)
    )

    resposta = api_autenticada.post(reverse("proposta-aceitar", args=[criada.data["id"]]))

    assert resposta.status_code == 400
    assert "expirada" in str(resposta.data["campos"]["status"]).lower()


def test_proposta_ja_respondida_nao_e_aceita_de_novo(
    api_autenticada, lead, imovel_disponivel
):
    criada = api_autenticada.post(
        reverse("proposta-list"), payload_proposta(lead, imovel_disponivel), format="json"
    )
    api_autenticada.post(
        reverse("proposta-recusar", args=[criada.data["id"]]),
        {"motivo": "abaixo do mínimo"},
        format="json",
    )

    resposta = api_autenticada.post(reverse("proposta-aceitar", args=[criada.data["id"]]))

    assert resposta.status_code == 400


def test_desconto_percentual_e_calculado(api_autenticada, lead, imovel_disponivel):
    imovel_disponivel.valor_venda = "400000.00"
    imovel_disponivel.finalidade = "VENDA"
    imovel_disponivel.save(update_fields=["valor_venda", "finalidade"])

    criada = api_autenticada.post(
        reverse("proposta-list"),
        payload_proposta(lead, imovel_disponivel, "360000.00"),
        format="json",
    )

    assert float(criada.data["desconto_percentual"]) == 10.0


def test_propostas_vencidas_viram_expiradas_na_rotina(
    api_autenticada, lead, imovel_disponivel
):
    from apps.crm.models import Proposta
    from apps.crm.tasks import expirar_propostas_vencidas

    criada = api_autenticada.post(
        reverse("proposta-list"), payload_proposta(lead, imovel_disponivel), format="json"
    )
    Proposta.objects.filter(pk=criada.data["id"]).update(
        validade=timezone.localdate() - timedelta(days=1)
    )

    assert expirar_propostas_vencidas() == 1
    assert Proposta.objects.get(pk=criada.data["id"]).status == StatusProposta.EXPIRADA
