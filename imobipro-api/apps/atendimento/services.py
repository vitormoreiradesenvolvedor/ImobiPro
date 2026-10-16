"""Regras do atendimento: abrir, distribuir, responder e encerrar o ticket."""

import logging

from django.db import transaction
from django.utils import timezone

from apps.atendimento.models import (
    STATUS_ENCERRADOS,
    EventoTicket,
    StatusTicket,
    Ticket,
    TipoTicket,
)

logger = logging.getLogger(__name__)


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 na API."""


# Do aberto ao encerrado, sem pular etapa nem ressuscitar ticket fechado.
TRANSICOES = {
    StatusTicket.ABERTO: {
        StatusTicket.EM_ATENDIMENTO,
        StatusTicket.AGENDADO,
        StatusTicket.CANCELADO,
    },
    StatusTicket.EM_ATENDIMENTO: {
        StatusTicket.AGENDADO,
        StatusTicket.CONCLUIDO,
        StatusTicket.CANCELADO,
    },
    StatusTicket.AGENDADO: {
        StatusTicket.EM_ATENDIMENTO,
        StatusTicket.CONCLUIDO,
        StatusTicket.CANCELADO,
    },
    StatusTicket.CONCLUIDO: set(),
    StatusTicket.CANCELADO: set(),
}


def gerar_protocolo(tenant) -> str:
    """Numeração por ano, legível ao telefone: ATD-2026-000123."""

    ano = timezone.localdate().year
    ultimo = (
        Ticket.objects.select_for_update()
        .filter(tenant=tenant, protocolo__startswith=f"ATD-{ano}-")
        .order_by("-protocolo")
        .first()
    )
    sequencia = int(ultimo.protocolo.split("-")[-1]) + 1 if ultimo else 1
    return f"ATD-{ano}-{sequencia:06d}"


def registrar_evento(ticket, descricao, usuario=None, visivel_ao_cliente=True):
    return EventoTicket.objects.create(
        ticket=ticket,
        usuario=usuario,
        descricao=descricao,
        visivel_ao_cliente=visivel_ao_cliente,
    )


def proximo_analista(tenant, imovel=None):
    """Mesmo rodízio do funil: quem tem menos ticket aberto recebe o próximo.

    Reaproveitar a distribuição do CRM não é economia de código: é garantir que
    o cliente do site caia na mesma fila de quem já atende o funil, em vez de
    criar uma segunda fila que ninguém olha.
    """

    from django.db.models import Count, Q

    from apps.accounts.models import Papel, Usuario

    candidatos = Usuario.objects.filter(
        tenant=tenant, papel__in=[Papel.CORRETOR, Papel.GERENTE], ativo=True
    ).annotate(abertos=Count("tickets", filter=~Q(tickets__status__in=STATUS_ENCERRADOS)))

    # Quem captou o imóvel conhece o imóvel: tem preferência no atendimento.
    if imovel and imovel.captador_id:
        preferido = candidatos.filter(pk=imovel.captador_id).first()
        if preferido:
            return preferido

    return candidatos.order_by("abertos", "criado_em").first()


@transaction.atomic
def abrir_ticket(dados: dict, tenant, imovel=None, request=None) -> Ticket:
    """Abre o ticket já distribuído e com o lead do funil criado junto.

    Pedido de visita que não vira lead é oportunidade perdida: o comercial
    precisa do contato no funil, e o atendimento precisa do prazo.
    """

    ticket = Ticket.objects.create(
        tenant=tenant,
        protocolo=gerar_protocolo(tenant),
        tipo=dados.get("tipo", TipoTicket.VISITA),
        imovel=imovel,
        solicitante_nome=dados["solicitante_nome"],
        solicitante_email=dados.get("solicitante_email", ""),
        solicitante_telefone=dados.get("solicitante_telefone", ""),
        mensagem=dados.get("mensagem", ""),
        preferencia_data=dados.get("preferencia_data"),
        preferencia_periodo=dados.get("preferencia_periodo", ""),
    )

    analista = proximo_analista(tenant, imovel=imovel)
    if analista:
        ticket.analista = analista
        ticket.save(update_fields=["analista", "atualizado_em"])

    registrar_evento(
        ticket,
        f"Pedido recebido pelo site: {ticket.get_tipo_display().lower()}.",
    )
    if analista:
        registrar_evento(
            ticket,
            f"Encaminhado para {analista.nome_completo}.",
            visivel_ao_cliente=False,
        )
        _notificar(analista, ticket)

    ticket.lead = _lead_do_ticket(ticket, tenant, request=request)
    ticket.save(update_fields=["lead", "atualizado_em"])
    return ticket


def _lead_do_ticket(ticket, tenant, request=None):
    from apps.crm.models import OrigemLead
    from apps.crm.services import criar_lead

    return criar_lead(
        {
            "nome": ticket.solicitante_nome,
            "email": ticket.solicitante_email,
            "telefone": ticket.solicitante_telefone,
            "mensagem": ticket.mensagem or f"Pedido de visita {ticket.protocolo}.",
            "origem": OrigemLead.SITE,
            "imovel_interesse": ticket.imovel,
        },
        tenant,
        request=request,
    )


def _notificar(usuario, ticket):
    from apps.notificacoes.models import TipoNotificacao
    from apps.notificacoes.services import notificar_usuario

    imovel = f" sobre {ticket.imovel.codigo}" if ticket.imovel else ""
    notificar_usuario(
        usuario,
        TipoNotificacao.TICKET_NOVO,
        titulo=f"Pedido de visita {ticket.protocolo}",
        descricao=f"{ticket.solicitante_nome} pediu contato{imovel}.",
        dados={"ticket_id": str(ticket.pk)},
    )


def registrar_primeira_resposta(ticket, usuario=None):
    """Para o cronômetro do SLA. Só a primeira resposta conta."""

    if ticket.primeira_resposta_em:
        return ticket
    ticket.primeira_resposta_em = timezone.now()
    ticket.save(update_fields=["primeira_resposta_em", "atualizado_em"])
    registrar_evento(
        ticket, "Primeiro contato registrado.", usuario=usuario, visivel_ao_cliente=False
    )
    return ticket


@transaction.atomic
def mover_status(ticket, novo_status, usuario=None, observacao="", agendado_para=None):
    if novo_status == ticket.status:
        return ticket

    if novo_status not in TRANSICOES[ticket.status]:
        raise RegraDeNegocio(
            f"Não dá para ir de {ticket.get_status_display().lower()} "
            f"para {StatusTicket(novo_status).label.lower()}."
        )

    if novo_status == StatusTicket.AGENDADO and not agendado_para:
        raise RegraDeNegocio("Informe a data e a hora da visita para agendar.")

    anterior = ticket.get_status_display()
    ticket.status = novo_status
    campos = ["status", "atualizado_em"]

    if agendado_para:
        ticket.agendado_para = agendado_para
        campos.append("agendado_para")
    if novo_status in STATUS_ENCERRADOS:
        ticket.encerrado_em = timezone.now()
        campos.append("encerrado_em")

    ticket.save(update_fields=campos)
    registrar_primeira_resposta(ticket, usuario=usuario)

    texto = f"{anterior} para {ticket.get_status_display()}."
    registrar_evento(ticket, texto + (f" {observacao}" if observacao else ""), usuario)

    if novo_status == StatusTicket.AGENDADO:
        _agendar_visita(ticket, usuario)
    return ticket


def _agendar_visita(ticket, usuario=None):
    """A visita confirmada entra na agenda do corretor, não só no ticket."""

    if not (ticket.imovel and ticket.lead and ticket.agendado_para):
        return None

    from apps.crm.models import Visita

    return Visita.objects.create(
        tenant=ticket.tenant,
        lead=ticket.lead,
        imovel=ticket.imovel,
        corretor=ticket.analista or usuario,
        agendada_para=ticket.agendado_para,
    )


@transaction.atomic
def reatribuir(ticket, analista, usuario=None, motivo=""):
    if ticket.status in STATUS_ENCERRADOS:
        raise RegraDeNegocio("Ticket encerrado não é reatribuído.")

    anterior = ticket.analista
    ticket.analista = analista
    ticket.save(update_fields=["analista", "atualizado_em"])

    de = f"de {anterior.nome_completo} " if anterior else ""
    registrar_evento(
        ticket,
        f"Atendimento passou {de}para {analista.nome_completo}."
        + (f" Motivo: {motivo}" if motivo else ""),
        usuario=usuario,
        visivel_ao_cliente=False,
    )
    _notificar(analista, ticket)
    return ticket


def responder(ticket, mensagem, usuario=None, visivel_ao_cliente=True):
    """Resposta ao interessado; a primeira encerra o cronômetro do SLA."""

    if not mensagem.strip():
        raise RegraDeNegocio("Escreva a resposta antes de enviar.")

    if ticket.status == StatusTicket.ABERTO:
        mover_status(ticket, StatusTicket.EM_ATENDIMENTO, usuario=usuario)
    else:
        registrar_primeira_resposta(ticket, usuario=usuario)

    return registrar_evento(
        ticket, mensagem, usuario=usuario, visivel_ao_cliente=visivel_ao_cliente
    )
