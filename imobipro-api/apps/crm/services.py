"""Regras do funil: distribuição, SLA, movimentação e propostas."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import Papel
from apps.crm.models import (
    ESTAGIOS_FECHADOS,
    MINUTOS_SLA_PRIMEIRO_CONTATO,
    EstagioLead,
    Interacao,
    Lead,
    Proposta,
    StatusProposta,
    TipoInteracao,
    Visita,
)
from apps.imoveis.models import SituacaoImovel
from apps.notificacoes.models import TipoNotificacao
from apps.notificacoes.services import notificar_equipe, notificar_usuario


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 na API."""


def registrar_interacao(lead, tipo, descricao, usuario=None):
    return Interacao.objects.create(
        lead=lead,
        tipo=tipo,
        descricao=descricao,
        usuario=usuario if usuario and usuario.is_authenticated else None,
    )


# ------------------------------------------------------------- distribuição


def proximo_corretor(tenant, imovel=None, excluir=None):
    """Round-robin justo: quem tem menos lead aberto recebe o próximo.

    Empate é desfeito por quem está há mais tempo sem receber assim o rodízio
    não trava no mesmo corretor quando todos estão zerados.
    """

    from apps.accounts.models import Usuario

    candidatos = Usuario.objects.filter(
        tenant=tenant, papel=Papel.CORRETOR, ativo=True
    ).annotate(abertos=Count("leads", filter=~Q(leads__estagio__in=ESTAGIOS_FECHADOS)))

    if excluir is not None:
        candidatos = candidatos.exclude(pk=excluir.pk)

    # Captador do imóvel tem preferência quando o lead veio por aquele imóvel.
    if imovel and imovel.captador_id:
        preferido = candidatos.filter(pk=imovel.captador_id).first()
        if preferido:
            return preferido

    return candidatos.order_by("abertos", "criado_em").first()


def atribuir_lead(lead, corretor, request=None, motivo="distribuição automática"):
    anterior = lead.corretor
    lead.corretor = corretor
    lead.atribuido_em = timezone.now()
    lead.save(update_fields=["corretor", "atribuido_em", "atualizado_em"])

    registrar_interacao(
        lead,
        TipoInteracao.SISTEMA,
        f"Lead atribuído a {corretor.nome_completo} ({motivo}).",
        usuario=getattr(request, "user", None),
    )

    notificar_usuario(
        corretor,
        tipo=TipoNotificacao.LEAD_NOVO,
        titulo=f"Novo lead: {lead.nome}",
        descricao=(
            f"{lead.get_origem_display()}"
            + (f" {lead.imovel_interesse.codigo}" if lead.imovel_interesse_id else "")
        ),
        dados={"lead_id": str(lead.pk)},
    )

    return anterior


def criar_lead(dados, tenant, request=None, distribuir=True):
    with transaction.atomic():
        lead = Lead.objects.create(tenant=tenant, **dados)

    registrar_interacao(
        lead,
        TipoInteracao.SISTEMA,
        f"Lead recebido via {lead.get_origem_display()}.",
        usuario=getattr(request, "user", None),
    )

    if distribuir and not lead.corretor_id:
        corretor = proximo_corretor(tenant, lead.imovel_interesse)
        if corretor:
            atribuir_lead(lead, corretor, request=request)
        else:
            notificar_equipe(
                tenant,
                [Papel.ADMIN, Papel.GERENTE],
                tipo=TipoNotificacao.LEAD_NOVO,
                titulo=f"Lead sem corretor disponível: {lead.nome}",
                descricao="Nenhum corretor ativo para receber a distribuição.",
                dados={"lead_id": str(lead.pk)},
            )
    elif lead.corretor_id:
        lead.atribuido_em = timezone.now()
        lead.save(update_fields=["atribuido_em"])

    return lead


# ---------------------------------------------------------------------- SLA


def marcar_primeiro_contato(lead):
    """Fecha o cronômetro do SLA na primeira interação humana com o lead."""

    if lead.primeiro_contato_em:
        return lead

    agora = timezone.now()
    lead.primeiro_contato_em = agora
    lead.sla_cumprido = lead.prazo_sla is None or agora <= lead.prazo_sla
    if lead.estagio == EstagioLead.NOVO:
        lead.estagio = EstagioLead.EM_CONTATO

    lead.save(
        update_fields=["primeiro_contato_em", "sla_cumprido", "estagio", "atualizado_em"]
    )
    return lead


def leads_com_sla_estourado(tenant):
    """Leads atribuídos há mais de 15 minutos e ainda sem nenhum contato."""

    limite = timezone.now() - timedelta(minutes=MINUTOS_SLA_PRIMEIRO_CONTATO)
    return Lead.objects.filter(
        tenant=tenant,
        primeiro_contato_em__isnull=True,
        estagio=EstagioLead.NOVO,
        corretor__isnull=False,
        atribuido_em__lt=limite,
    ).select_related("corretor")


def devolver_lead_para_fila(lead, request=None):
    """SLA estourado: o lead volta para a fila e a gestão fica sabendo."""

    corretor_anterior = lead.corretor
    lead.sla_cumprido = False
    lead.save(update_fields=["sla_cumprido"])

    # Quem deixou estourar não recebe o lead de volta.
    novo = proximo_corretor(lead.tenant, lead.imovel_interesse, excluir=corretor_anterior)
    if novo:
        atribuir_lead(lead, novo, request=request, motivo="SLA estourado")

    notificar_equipe(
        lead.tenant,
        [Papel.ADMIN, Papel.GERENTE],
        tipo=TipoNotificacao.SLA_ESTOURADO,
        titulo=f"SLA estourado: {lead.nome}",
        descricao=(
            f"{corretor_anterior.nome_completo} não atendeu em "
            f"{MINUTOS_SLA_PRIMEIRO_CONTATO} minutos."
            if corretor_anterior
            else "Lead sem atendimento no prazo."
        ),
        dados={"lead_id": str(lead.pk)},
    )
    return lead


# --------------------------------------------------------------- movimentação


def mover_estagio(lead, novo_estagio, request=None, motivo_perda="", observacao=""):
    if novo_estagio == lead.estagio:
        return lead

    if novo_estagio == EstagioLead.FECHADO_PERDIDO and not motivo_perda:
        raise RegraDeNegocio("Informe o motivo da perda para fechar o lead.")

    anterior = lead.get_estagio_display()
    lead.estagio = novo_estagio
    campos = ["estagio", "atualizado_em"]

    if novo_estagio in ESTAGIOS_FECHADOS:
        lead.fechado_em = timezone.now()
        campos.append("fechado_em")
    if novo_estagio == EstagioLead.FECHADO_PERDIDO:
        lead.motivo_perda = motivo_perda
        lead.observacao_perda = observacao
        campos += ["motivo_perda", "observacao_perda"]

    lead.save(update_fields=campos)

    registrar_interacao(
        lead,
        TipoInteracao.SISTEMA,
        f"{anterior} → {lead.get_estagio_display()}"
        + (f" ({lead.get_motivo_perda_display()})" if lead.motivo_perda else "."),
        usuario=getattr(request, "user", None),
    )
    return lead


# ------------------------------------------------------------------- visitas


def agendar_visita(lead, imovel, agendada_para, request=None, corretor=None):
    if agendada_para < timezone.now():
        raise RegraDeNegocio("Não é possível agendar visita no passado.")

    if not imovel.disponivel_para_negocio:
        raise RegraDeNegocio(
            f"Imóvel {imovel.get_situacao_display().lower()} não recebe visita."
        )

    visita = Visita.objects.create(
        tenant=lead.tenant,
        lead=lead,
        imovel=imovel,
        corretor=corretor or lead.corretor,
        agendada_para=agendada_para,
    )

    registrar_interacao(
        lead,
        TipoInteracao.VISITA,
        f"Visita agendada em {imovel.codigo} para {agendada_para:%d/%m/%Y %H:%M}.",
        usuario=getattr(request, "user", None),
    )
    marcar_primeiro_contato(lead)

    if lead.estagio in {EstagioLead.NOVO, EstagioLead.EM_CONTATO, EstagioLead.QUALIFICADO}:
        mover_estagio(lead, EstagioLead.VISITA_AGENDADA, request=request)

    return visita


def registrar_feedback_visita(visita, feedback, interesse, request=None):
    visita.realizada = True
    visita.feedback = feedback
    visita.interesse_pos_visita = interesse
    visita.save(update_fields=["realizada", "feedback", "interesse_pos_visita"])

    registrar_interacao(
        visita.lead,
        TipoInteracao.VISITA,
        f"Visita realizada em {visita.imovel.codigo}: {feedback}",
        usuario=getattr(request, "user", None),
    )

    if visita.lead.estagio == EstagioLead.VISITA_AGENDADA:
        mover_estagio(visita.lead, EstagioLead.VISITA_REALIZADA, request=request)

    return visita


# ------------------------------------------------------------------ propostas


def criar_proposta(lead, imovel, dados, request=None):
    if not imovel.disponivel_para_negocio:
        raise RegraDeNegocio(
            f"Imóvel {imovel.get_situacao_display().lower()} não aceita proposta."
        )

    proposta = Proposta.objects.create(
        tenant=lead.tenant,
        lead=lead,
        imovel=imovel,
        criada_por=getattr(request, "user", None) if request else None,
        **dados,
    )

    registrar_interacao(
        lead,
        TipoInteracao.PROPOSTA,
        f"Proposta de R$ {proposta.valor_ofertado} em {imovel.codigo}.",
        usuario=getattr(request, "user", None),
    )

    if lead.estagio not in ESTAGIOS_FECHADOS:
        mover_estagio(lead, EstagioLead.PROPOSTA, request=request)

    notificar_equipe(
        lead.tenant,
        [Papel.ADMIN, Papel.GERENTE],
        tipo=TipoNotificacao.PROPOSTA_RECEBIDA,
        titulo=f"Proposta em {imovel.codigo}",
        descricao=f"{lead.nome} ofertou R$ {proposta.valor_ofertado}.",
        dados={"proposta_id": str(proposta.pk), "lead_id": str(lead.pk)},
    )

    return proposta


@transaction.atomic
def aceitar_proposta(proposta, request=None):
    """Aceite reserva o imóvel e prepara o rascunho de contrato."""

    from apps.imoveis.services import mudar_situacao

    if proposta.status in {StatusProposta.ACEITA, StatusProposta.RECUSADA}:
        raise RegraDeNegocio("Esta proposta já foi respondida.")
    if proposta.expirada:
        raise RegraDeNegocio("Proposta expirada. Peça uma nova ao cliente.")

    proposta.status = StatusProposta.ACEITA
    proposta.respondida_em = timezone.now()
    proposta.save(update_fields=["status", "respondida_em"])

    # As demais propostas do mesmo imóvel perdem a validade.
    Proposta.objects.filter(imovel=proposta.imovel, status=StatusProposta.ENVIADA).exclude(
        pk=proposta.pk
    ).update(status=StatusProposta.RECUSADA, respondida_em=timezone.now())

    if proposta.imovel.situacao == SituacaoImovel.DISPONIVEL:
        mudar_situacao(
            proposta.imovel,
            SituacaoImovel.RESERVADO,
            request=request,
            motivo="proposta aceita",
        )

    mover_estagio(proposta.lead, EstagioLead.NEGOCIACAO, request=request)
    registrar_interacao(
        proposta.lead,
        TipoInteracao.PROPOSTA,
        f"Proposta de R$ {proposta.valor_ofertado} aceita.",
        usuario=getattr(request, "user", None),
    )
    return proposta


def recusar_proposta(proposta, motivo="", request=None):
    if proposta.status in {StatusProposta.ACEITA, StatusProposta.RECUSADA}:
        raise RegraDeNegocio("Esta proposta já foi respondida.")

    proposta.status = StatusProposta.RECUSADA
    proposta.observacao_resposta = motivo
    proposta.respondida_em = timezone.now()
    proposta.save(update_fields=["status", "observacao_resposta", "respondida_em"])

    registrar_interacao(
        proposta.lead,
        TipoInteracao.PROPOSTA,
        f"Proposta recusada{f': {motivo}' if motivo else '.'}",
        usuario=getattr(request, "user", None),
    )
    return proposta
