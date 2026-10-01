"""Assinatura de webhook, payload de portal e envio de WhatsApp."""

import hashlib
import hmac
import logging

from django.utils import timezone

from apps.integracoes.models import EventoIntegracao, IntegracaoPortal, StatusEnvio

logger = logging.getLogger(__name__)


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 na API."""


def assinar(corpo: bytes, segredo: str) -> str:
    """HMAC-SHA256 no formato `sha256=<hex>`, padrão dos portais."""
    return "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()


def assinatura_valida(corpo: bytes, assinatura_recebida: str, segredo: str) -> bool:
    """Comparação em tempo constante: comparar com `==` vaza o segredo."""
    if not assinatura_recebida:
        return False
    return hmac.compare_digest(assinar(corpo, segredo), assinatura_recebida)


def integracao_do_portal(tenant, portal):
    return IntegracaoPortal.objects.filter(tenant=tenant, portal=portal, ativo=True).first()


def registrar_evento(
    tenant,
    evento,
    payload,
    portal="",
    direcao="ENTRADA",
    status=StatusEnvio.PENDENTE,
    referencia="",
):
    return EventoIntegracao.objects.create(
        tenant=tenant,
        portal=portal,
        direcao=direcao,
        evento=evento,
        payload=payload,
        status=status,
        referencia=referencia,
    )


# ------------------------------------------------------ lead vindo de portal


# Cada portal nomeia os campos do seu jeito; normalizamos na entrada.
MAPA_DE_CAMPOS = {
    "nome": ["nome", "name", "lead_name", "client_name"],
    "email": ["email", "e_mail", "lead_email"],
    "telefone": ["telefone", "phone", "telephone", "lead_phone", "celular"],
    "mensagem": ["mensagem", "message", "comment", "observacao"],
    "codigo_imovel": ["codigo", "listing_id", "external_id", "imovel", "reference"],
}


def normalizar_lead(payload: dict) -> dict:
    def primeiro(chaves):
        for chave in chaves:
            valor = payload.get(chave)
            if valor:
                return str(valor).strip()
        return ""

    return {campo: primeiro(chaves) for campo, chaves in MAPA_DE_CAMPOS.items()}


def processar_lead_de_portal(tenant, portal, payload, request=None):
    """Cria o lead a partir do webhook, já distribuído pelo round-robin."""

    from apps.crm.models import OrigemLead
    from apps.crm.services import criar_lead
    from apps.imoveis.models import Imovel

    dados = normalizar_lead(payload)

    if not dados["nome"]:
        raise RegraDeNegocio("Payload sem nome do interessado.")
    if not dados["email"] and not dados["telefone"]:
        raise RegraDeNegocio("Payload sem e-mail nem telefone.")

    imovel = None
    if dados["codigo_imovel"]:
        imovel = Imovel.objects.filter(tenant=tenant, codigo=dados["codigo_imovel"]).first()

    lead = criar_lead(
        {
            "nome": dados["nome"],
            "email": dados["email"],
            "telefone": dados["telefone"],
            "mensagem": dados["mensagem"],
            "origem": OrigemLead.PORTAL,
            "imovel_interesse": imovel,
        },
        tenant,
        request=request,
    )

    registrar_evento(
        tenant,
        "lead_recebido",
        payload,
        portal=portal,
        status=StatusEnvio.ENVIADO,
        referencia=str(lead.pk),
    )
    return lead


# ------------------------------------------------- publicação nos portais


def payload_do_imovel(imovel):
    """Formato neutro; cada conector traduz para o esquema do seu portal."""

    return {
        "codigo": imovel.codigo,
        "titulo": imovel.titulo,
        "descricao": imovel.descricao,
        "tipo": imovel.tipo,
        "finalidade": imovel.finalidade,
        "valor_venda": str(imovel.valor_venda) if imovel.valor_venda else None,
        "valor_locacao": str(imovel.valor_locacao) if imovel.valor_locacao else None,
        "valor_condominio": str(imovel.valor_condominio or 0),
        "valor_iptu": str(imovel.valor_iptu_anual or 0),
        "quartos": imovel.quartos,
        "suites": imovel.suites,
        "banheiros": imovel.banheiros,
        "vagas": imovel.vagas,
        "area_util": str(imovel.area_util) if imovel.area_util else None,
        "endereco": {
            "cep": imovel.endereco.cep,
            "logradouro": imovel.endereco.logradouro,
            "numero": imovel.endereco.numero,
            "bairro": imovel.endereco.bairro,
            "cidade": imovel.endereco.cidade,
            "uf": imovel.endereco.uf,
            "latitude": str(imovel.endereco.latitude or ""),
            "longitude": str(imovel.endereco.longitude or ""),
        },
        "caracteristicas": [c.slug for c in imovel.caracteristicas.all()],
        "fotos": [foto.arquivo.url for foto in imovel.fotos.all()],
        "atualizado_em": imovel.atualizado_em.isoformat(),
    }


def enfileirar_publicacao(imovel, portal):
    """Enfileira o envio. O worker faz o POST e trata retry/dead-letter."""

    integracao = integracao_do_portal(imovel.tenant, portal)
    if not integracao:
        raise RegraDeNegocio(f"Integração com {portal} não está configurada.")

    return registrar_evento(
        imovel.tenant,
        "publicar_imovel",
        payload_do_imovel(imovel),
        portal=portal,
        direcao="SAIDA",
        referencia=imovel.codigo,
    )


def marcar_evento(evento, status, erro=""):
    evento.status = status
    evento.tentativas += 1
    evento.erro = erro[:2000]
    evento.save(update_fields=["status", "tentativas", "erro", "atualizado_em"])
    return evento


def sincronizar_portal(integracao):
    """Enfileira todos os imóveis publicados que mudaram desde a última carga."""

    from apps.imoveis.models import Imovel

    consulta = (
        Imovel.objects.filter(
            tenant=integracao.tenant, publicado_site=True, deletado_em__isnull=True
        )
        .select_related("endereco")
        .prefetch_related("fotos", "caracteristicas")
    )

    if integracao.ultima_sincronizacao:
        consulta = consulta.filter(atualizado_em__gt=integracao.ultima_sincronizacao)

    enfileirados = 0
    for imovel in consulta:
        registrar_evento(
            integracao.tenant,
            "publicar_imovel",
            payload_do_imovel(imovel),
            portal=integracao.portal,
            direcao="SAIDA",
            referencia=imovel.codigo,
        )
        enfileirados += 1

    integracao.ultima_sincronizacao = timezone.now()
    integracao.total_publicados = consulta.count()
    integracao.save(update_fields=["ultima_sincronizacao", "total_publicados"])
    return enfileirados


# ---------------------------------------------------------------- WhatsApp


def enviar_whatsapp(tenant, telefone, mensagem, referencia=""):
    """Registra a mensagem para envio pela WhatsApp Business API.

    O envio real depende das credenciais do cliente; até que estejam
    configuradas, o evento fica PENDENTE e aparece no painel de integrações
    nunca desaparece silenciosamente.
    """

    if not telefone:
        raise RegraDeNegocio("Sem telefone para enviar a mensagem.")

    return registrar_evento(
        tenant,
        "whatsapp_saida",
        {"telefone": telefone, "mensagem": mensagem},
        direcao="SAIDA",
        referencia=referencia,
    )
