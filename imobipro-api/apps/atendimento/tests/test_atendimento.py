"""Ticket de visita: o site abre, a equipe atende, o cliente acompanha.

O interessado não tem conta. Tudo que ele tem é o protocolo, e é por isso que a
consulta pública exige também o contato usado na abertura.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.atendimento.models import (
    MINUTOS_SLA_PRIMEIRA_RESPOSTA,
    StatusTicket,
    Ticket,
    TipoTicket,
)
from apps.atendimento.services import (
    RegraDeNegocio,
    abrir_ticket,
    mover_status,
    reatribuir,
    responder,
)
from apps.atendimento.tests.factories import TicketFactory
from apps.imoveis.services import publicar
from apps.imoveis.tests.factories import ImovelFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def publicado(tenant, proprietario, corretor):
    imovel = ImovelFactory(
        tenant=tenant, proprietario=proprietario, captador=corretor, com_fotos=5
    )
    return publicar(imovel)


def url_abertura(tenant):
    return reverse("ticket-publico-abrir", kwargs={"subdominio": tenant.subdominio})


def url_acompanhamento(tenant, protocolo):
    return reverse(
        "ticket-publico-acompanhar",
        kwargs={"subdominio": tenant.subdominio, "protocolo": protocolo},
    )


PEDIDO = {
    "tipo": "VISITA",
    "solicitante_nome": "Marina Interessada",
    "solicitante_telefone": "(35) 99123-4567",
    "solicitante_email": "marina@teste.local",
    "mensagem": "Posso visitar no sábado?",
    "preferencia_periodo": "MANHA",
}


# ------------------------------------------------------------ abertura pública


def test_site_abre_ticket_sem_login_e_devolve_protocolo(api, tenant, publicado):
    resposta = api.post(
        url_abertura(tenant), {**PEDIDO, "imovel_codigo": publicado.codigo}, format="json"
    )

    assert resposta.status_code == 201
    assert resposta.data["protocolo"].startswith("ATD-")
    assert Ticket.objects.count() == 1


def test_pedido_de_visita_tambem_entra_no_funil(api, tenant, publicado):
    """Pedido que não vira lead é oportunidade perdida."""

    api.post(
        url_abertura(tenant), {**PEDIDO, "imovel_codigo": publicado.codigo}, format="json"
    )

    ticket = Ticket.objects.get()
    assert ticket.lead is not None
    assert ticket.lead.imovel_interesse == publicado
    assert ticket.lead.corretor is not None


def test_ticket_nasce_com_analista_responsavel(api, tenant, publicado, corretor):
    """Quem captou o imóvel conhece o imóvel: atende primeiro."""

    api.post(
        url_abertura(tenant), {**PEDIDO, "imovel_codigo": publicado.codigo}, format="json"
    )

    assert Ticket.objects.get().analista == corretor


def test_pedido_sem_contato_nenhum_e_recusado(api, tenant):
    resposta = api.post(
        url_abertura(tenant),
        {"solicitante_nome": "Sem Contato"},
        format="json",
    )

    assert resposta.status_code == 400
    assert "telefone" in str(resposta.data["campos"]).lower()


def test_imovel_fora_do_site_nao_abre_ticket(api, tenant, proprietario):
    fora = ImovelFactory(tenant=tenant, proprietario=proprietario)

    resposta = api.post(
        url_abertura(tenant), {**PEDIDO, "imovel_codigo": fora.codigo}, format="json"
    )

    assert resposta.status_code == 400


# --------------------------------------------------------- acompanhamento


def test_cliente_acompanha_pelo_protocolo_e_contato(api, tenant, publicado):
    api.post(
        url_abertura(tenant), {**PEDIDO, "imovel_codigo": publicado.codigo}, format="json"
    )
    ticket = Ticket.objects.get()

    resposta = api.get(
        url_acompanhamento(tenant, ticket.protocolo), {"contato": "35991234567"}
    )

    assert resposta.status_code == 200
    assert resposta.data["status"] == StatusTicket.ABERTO
    assert resposta.data["imovel_codigo"] == publicado.codigo


def test_protocolo_sozinho_nao_abre_o_historico(api, tenant, publicado):
    """Número sequencial é fácil de adivinhar; o histórico tem dado de pessoa."""

    api.post(
        url_abertura(tenant), {**PEDIDO, "imovel_codigo": publicado.codigo}, format="json"
    )
    ticket = Ticket.objects.get()

    sem_contato = api.get(url_acompanhamento(tenant, ticket.protocolo))
    contato_errado = api.get(
        url_acompanhamento(tenant, ticket.protocolo), {"contato": "11988887777"}
    )

    assert sem_contato.status_code == 400
    assert contato_errado.status_code == 404


def test_nota_interna_nao_aparece_para_o_cliente(api, tenant, publicado, corretor):
    api.post(
        url_abertura(tenant), {**PEDIDO, "imovel_codigo": publicado.codigo}, format="json"
    )
    ticket = Ticket.objects.get()
    responder(
        ticket, "Cliente parece indeciso.", usuario=corretor, visivel_ao_cliente=False
    )

    resposta = api.get(
        url_acompanhamento(tenant, ticket.protocolo), {"contato": "marina@teste.local"}
    )

    descricoes = [evento["descricao"] for evento in resposta.data["eventos"]]
    assert "Cliente parece indeciso." not in descricoes


# ------------------------------------------------------------------- esteira


def test_primeira_resposta_para_o_cronometro(tenant, corretor, publicado):
    ticket = abrir_ticket(dict(PEDIDO), tenant, imovel=publicado)

    responder(ticket, "Podemos sábado às 10h.", usuario=corretor)
    ticket.refresh_from_db()

    assert ticket.primeira_resposta_em is not None
    assert ticket.status == StatusTicket.EM_ATENDIMENTO
    assert ticket.sla_estourado is False


def test_sla_estoura_quando_ninguem_responde(tenant, publicado):
    ticket = abrir_ticket(dict(PEDIDO), tenant, imovel=publicado)
    Ticket.objects.filter(pk=ticket.pk).update(
        criado_em=timezone.now() - timedelta(minutes=MINUTOS_SLA_PRIMEIRA_RESPOSTA + 5)
    )
    ticket.refresh_from_db()

    assert ticket.sla_estourado is True
    assert ticket.minutos_para_resposta < 0


def test_agendar_visita_exige_data(tenant, corretor, publicado):
    ticket = abrir_ticket(dict(PEDIDO), tenant, imovel=publicado)

    with pytest.raises(RegraDeNegocio, match="data e a hora"):
        mover_status(ticket, StatusTicket.AGENDADO, usuario=corretor)


def test_agendamento_cria_a_visita_na_agenda(tenant, corretor, publicado):
    """Visita combinada no ticket precisa aparecer na agenda de quem vai."""

    from apps.crm.models import Visita

    ticket = abrir_ticket(dict(PEDIDO), tenant, imovel=publicado)
    quando = timezone.now() + timedelta(days=2)

    mover_status(ticket, StatusTicket.AGENDADO, usuario=corretor, agendado_para=quando)

    visita = Visita.objects.get(lead=ticket.lead)
    assert visita.imovel == publicado
    assert visita.agendada_para == quando


def test_ticket_encerrado_nao_volta_atras(tenant, corretor, publicado):
    ticket = abrir_ticket(dict(PEDIDO), tenant, imovel=publicado)
    mover_status(ticket, StatusTicket.CANCELADO, usuario=corretor)

    with pytest.raises(RegraDeNegocio):
        mover_status(ticket, StatusTicket.EM_ATENDIMENTO, usuario=corretor)


def test_reatribuicao_registra_quem_passou_para_quem(tenant, corretor, gerente, publicado):
    ticket = abrir_ticket(dict(PEDIDO), tenant, imovel=publicado)

    reatribuir(ticket, gerente, usuario=corretor, motivo="corretor de férias")
    ticket.refresh_from_db()

    assert ticket.analista == gerente
    interno = ticket.eventos.filter(visivel_ao_cliente=False).last()
    assert "férias" in interno.descricao


def test_ticket_encerrado_nao_e_reatribuido(tenant, corretor, gerente, publicado):
    ticket = abrir_ticket(dict(PEDIDO), tenant, imovel=publicado)
    # Concluir exige ter passado pelo atendimento: ninguém fecha o que não abriu.
    mover_status(ticket, StatusTicket.EM_ATENDIMENTO, usuario=corretor)
    mover_status(ticket, StatusTicket.CONCLUIDO, usuario=corretor)

    with pytest.raises(RegraDeNegocio, match="encerrado"):
        reatribuir(ticket, gerente, usuario=corretor)


# --------------------------------------------------------------- fila interna


def test_painel_mostra_o_que_precisa_de_resposta(api_autenticada, tenant, publicado):
    abrir_ticket(dict(PEDIDO), tenant, imovel=publicado)
    antigo = TicketFactory(tenant=tenant, tipo=TipoTicket.INFORMACAO)
    Ticket.objects.filter(pk=antigo.pk).update(
        criado_em=timezone.now() - timedelta(hours=3)
    )

    resposta = api_autenticada.get(reverse("ticket-painel"))

    assert resposta.status_code == 200
    assert resposta.data["abertos"] == 2
    assert resposta.data["sem_resposta"] == 2
    assert resposta.data["sla_estourado"] == 1


def test_fila_de_outra_imobiliaria_nao_aparece(api_autenticada, outro_tenant):
    TicketFactory(tenant=outro_tenant)

    resposta = api_autenticada.get(reverse("ticket-list"))

    assert resposta.data["count"] == 0
