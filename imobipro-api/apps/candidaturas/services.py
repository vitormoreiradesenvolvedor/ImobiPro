"""Regras da candidatura: documentação, análise e virada para contrato."""

import logging

from django.db import transaction
from django.utils import timezone

from apps.candidaturas.models import (
    STATUS_ENCERRADOS,
    Candidatura,
    DocumentoCandidatura,
    EventoCandidatura,
    StatusCandidatura,
    StatusDocumento,
)

logger = logging.getLogger(__name__)

# Regra de mercado que a imobiliária configura por contrato; aqui vale como
# recomendação na tela de análise, nunca como recusa automática.
RENDA_MINIMA_SUGERIDA = 3


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 na API."""


TRANSICOES = {
    StatusCandidatura.RASCUNHO: {
        StatusCandidatura.EM_ANALISE,
        StatusCandidatura.DESISTIU,
    },
    StatusCandidatura.EM_ANALISE: {
        StatusCandidatura.PENDENTE,
        StatusCandidatura.APROVADA,
        StatusCandidatura.REPROVADA,
        StatusCandidatura.DESISTIU,
    },
    StatusCandidatura.PENDENTE: {
        StatusCandidatura.EM_ANALISE,
        StatusCandidatura.REPROVADA,
        StatusCandidatura.DESISTIU,
    },
    StatusCandidatura.APROVADA: set(),
    StatusCandidatura.REPROVADA: set(),
    StatusCandidatura.DESISTIU: set(),
}


def gerar_protocolo(tenant) -> str:
    """Numeração própria, para o cliente não confundir com o do atendimento."""

    ano = timezone.localdate().year
    ultima = (
        Candidatura.objects.select_for_update()
        .filter(tenant=tenant, protocolo__startswith=f"CAD-{ano}-")
        .order_by("-protocolo")
        .first()
    )
    sequencia = int(ultima.protocolo.split("-")[-1]) + 1 if ultima else 1
    return f"CAD-{ano}-{sequencia:06d}"


def registrar_evento(candidatura, descricao, usuario=None, visivel_ao_cliente=True):
    return EventoCandidatura.objects.create(
        candidatura=candidatura,
        usuario=usuario,
        descricao=descricao,
        visivel_ao_cliente=visivel_ao_cliente,
    )


@transaction.atomic
def abrir_candidatura(dados: dict, tenant, imovel, ticket=None, usuario=None):
    """Abre a candidatura e devolve o link que o pretendente vai usar."""

    from apps.imoveis.models import SituacaoImovel

    if imovel.situacao not in {SituacaoImovel.DISPONIVEL, SituacaoImovel.RESERVADO}:
        raise RegraDeNegocio(
            f"{imovel.codigo} está como {imovel.get_situacao_display().lower()} "
            "e não aceita candidatura."
        )

    candidatura = Candidatura.objects.create(
        tenant=tenant,
        protocolo=gerar_protocolo(tenant),
        imovel=imovel,
        ticket=ticket,
        analista=usuario or (ticket.analista if ticket else None),
        pretendente_nome=dados["pretendente_nome"],
        pretendente_cpf=dados.get("pretendente_cpf", ""),
        pretendente_email=dados.get("pretendente_email", ""),
        pretendente_telefone=dados.get("pretendente_telefone", ""),
        renda_mensal=dados.get("renda_mensal"),
        ocupacao=dados.get("ocupacao", ""),
        observacoes=dados.get("observacoes", ""),
    )

    registrar_evento(
        candidatura,
        f"Candidatura aberta para {imovel.codigo}. Faltam os documentos.",
        usuario=usuario,
    )
    if ticket:
        from apps.atendimento.services import registrar_evento as evento_ticket

        evento_ticket(
            ticket,
            f"Candidatura {candidatura.protocolo} aberta a partir deste atendimento.",
            usuario=usuario,
            visivel_ao_cliente=False,
        )
    return candidatura


def anexar_documento(candidatura, tipo, arquivo, nome_original=""):
    """Envio pelo link do pretendente. Reenvio substitui o recusado."""

    if candidatura.status in STATUS_ENCERRADOS:
        raise RegraDeNegocio("Esta candidatura já foi encerrada.")

    documento = DocumentoCandidatura.objects.create(
        candidatura=candidatura,
        tipo=tipo,
        arquivo=arquivo,
        nome_original=nome_original[:160],
    )
    registrar_evento(candidatura, f"{documento.get_tipo_display()} enviado pelo cliente.")

    # Documentação completa tira a candidatura da espera sozinha: ninguém
    # precisa lembrar de mudar o status na mão.
    if candidatura.status in {StatusCandidatura.RASCUNHO, StatusCandidatura.PENDENTE}:
        if candidatura.documentacao_completa:
            mover_status(candidatura, StatusCandidatura.EM_ANALISE)
    return documento


def conferir_documento(documento, aprovado, usuario=None, observacao=""):
    if not aprovado and not observacao.strip():
        raise RegraDeNegocio("Diga o que está errado no documento recusado.")

    documento.conferir(aprovado, usuario=usuario, observacao=observacao)
    candidatura = documento.candidatura

    if aprovado:
        registrar_evento(
            candidatura,
            f"{documento.get_tipo_display()} conferido.",
            usuario=usuario,
        )
    else:
        registrar_evento(
            candidatura,
            f"{documento.get_tipo_display()} recusado: {observacao}",
            usuario=usuario,
        )
        if candidatura.status == StatusCandidatura.EM_ANALISE:
            mover_status(
                candidatura,
                StatusCandidatura.PENDENTE,
                usuario=usuario,
                observacao="Aguardando reenvio do cliente.",
            )
    return documento


@transaction.atomic
def mover_status(candidatura, novo_status, usuario=None, observacao=""):
    if novo_status == candidatura.status:
        return candidatura

    if novo_status not in TRANSICOES[candidatura.status]:
        raise RegraDeNegocio(
            f"Não dá para ir de {candidatura.get_status_display().lower()} "
            f"para {StatusCandidatura(novo_status).label.lower()}."
        )

    anterior = candidatura.get_status_display()
    candidatura.status = novo_status
    campos = ["status", "atualizado_em"]

    if novo_status in STATUS_ENCERRADOS:
        candidatura.decidido_em = timezone.now()
        candidatura.motivo_decisao = observacao
        campos += ["decidido_em", "motivo_decisao"]

    candidatura.save(update_fields=campos)
    registrar_evento(
        candidatura,
        f"{anterior} para {candidatura.get_status_display()}."
        + (f" {observacao}" if observacao else ""),
        usuario=usuario,
    )
    return candidatura


def _pendencias_para_aprovar(candidatura) -> list:
    pendencias = []
    if not candidatura.documentacao_completa:
        faltando = ", ".join(str(tipo.label) for tipo in candidatura.documentos_pendentes)
        pendencias.append(f"Faltam documentos: {faltando}.")

    recusados = candidatura.documentos.filter(status=StatusDocumento.RECUSADO).count()
    if recusados:
        pendencias.append(f"{recusados} documento(s) recusado(s) sem reenvio.")

    sem_conferir = candidatura.documentos.filter(status=StatusDocumento.ENVIADO).count()
    if sem_conferir:
        pendencias.append(f"{sem_conferir} documento(s) ainda sem conferência.")

    return pendencias


@transaction.atomic
def aprovar(candidatura, usuario=None, observacao=""):
    """Aprovação só depois da papelada conferida, item a item."""

    if pendencias := _pendencias_para_aprovar(candidatura):
        raise RegraDeNegocio(" ".join(pendencias))

    mover_status(
        candidatura, StatusCandidatura.APROVADA, usuario=usuario, observacao=observacao
    )
    candidatura.pessoa = _garantir_pessoa(candidatura)
    candidatura.save(update_fields=["pessoa", "atualizado_em"])

    registrar_evento(
        candidatura,
        f"Cadastro de {candidatura.pessoa.nome} criado para o contrato.",
        usuario=usuario,
        visivel_ao_cliente=False,
    )
    return candidatura


def _garantir_pessoa(candidatura):
    """A pessoa do contrato nasce da candidatura, sem redigitar nada.

    O documento é normalizado para dígitos, como no resto do sistema: gravar
    "529.982.247-25" aqui criaria um cadastro que a busca por CPF nunca acha e
    que duplicaria o cliente na próxima locação.
    """

    from django.core.exceptions import ValidationError as ErroDeValidacao

    from apps.core.validators import validar_cpf_cnpj
    from apps.pessoas.models import Pessoa

    if candidatura.pessoa:
        return candidatura.pessoa

    documento = ""
    if candidatura.pretendente_cpf:
        try:
            documento = validar_cpf_cnpj(candidatura.pretendente_cpf)
        except ErroDeValidacao as erro:
            raise RegraDeNegocio(
                f"CPF do pretendente inválido: {candidatura.pretendente_cpf}."
            ) from erro

        existente = Pessoa.objects.filter(
            tenant=candidatura.tenant, cpf_cnpj=documento
        ).first()
        if existente:
            return existente

    return Pessoa.objects.create(
        tenant=candidatura.tenant,
        nome=candidatura.pretendente_nome,
        cpf_cnpj=documento,
        email=candidatura.pretendente_email,
        telefone=candidatura.pretendente_telefone,
    )


@transaction.atomic
def gerar_contrato(candidatura, dados: dict, usuario=None, request=None):
    """Cria o rascunho do contrato com locador e locatário já preenchidos."""

    from apps.contratos.models import PapelParte, TipoContrato
    from apps.contratos.services import adicionar_parte, criar_contrato

    if candidatura.status != StatusCandidatura.APROVADA:
        raise RegraDeNegocio("Só candidatura aprovada vira contrato.")
    if candidatura.contrato:
        raise RegraDeNegocio(
            f"Esta candidatura já gerou o contrato {candidatura.contrato.numero}."
        )

    contrato = criar_contrato(
        {
            "tipo": TipoContrato.LOCACAO,
            "imovel": candidatura.imovel,
            "valor": dados.get("valor") or candidatura.imovel.valor_locacao,
            "data_inicio": dados["data_inicio"],
            "data_fim": dados["data_fim"],
            "dia_vencimento": dados.get("dia_vencimento", 10),
            "taxa_administracao_percent": dados.get("taxa_administracao_percent", 10),
            "garantia_tipo": dados.get("garantia_tipo", "CAUCAO"),
            "garantia_valor": dados.get("garantia_valor"),
        },
        candidatura.tenant,
        request=request,
    )

    adicionar_parte(contrato, candidatura.imovel.proprietario, PapelParte.LOCADOR)
    adicionar_parte(contrato, candidatura.pessoa, PapelParte.LOCATARIO)

    candidatura.contrato = contrato
    candidatura.save(update_fields=["contrato", "atualizado_em"])
    registrar_evento(
        candidatura,
        f"Contrato {contrato.numero} gerado a partir desta candidatura.",
        usuario=usuario,
    )
    return contrato
