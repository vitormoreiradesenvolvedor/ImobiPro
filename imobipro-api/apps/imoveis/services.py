"""Regras de negócio do imóvel.

Views e tasks chamam estas funções; nenhuma delas duplica regra.
"""

from datetime import timedelta

from django.contrib.postgres.search import SearchVector
from django.db import transaction
from django.utils import timezone

from apps.core.auditoria import Acao, registrar, snapshot
from apps.imoveis.models import (
    TRANSICOES_PERMITIDAS,
    HistoricoImovel,
    Imovel,
    SituacaoImovel,
    TipoEventoImovel,
)

CAMPOS_AUDITADOS = ["valor_venda", "valor_locacao", "situacao", "publicado_site"]


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 no handler da API."""


@transaction.atomic
def gerar_codigo(tenant) -> str:
    """Código sequencial por imobiliária: REF-000123.

    O contador vive no tenant e é lido com bloqueio de linha dois corretores
    cadastrando ao mesmo tempo não podem receber o mesmo código.
    """

    from apps.accounts.models import Tenant

    linha = Tenant.objects.select_for_update().get(pk=tenant.pk)
    linha.sequencia_imovel += 1
    linha.save(update_fields=["sequencia_imovel"])
    return f"REF-{linha.sequencia_imovel:06d}"


def atualizar_indice_busca(imovel: Imovel) -> None:
    """Recalcula o vetor de busca textual (GIN) do imóvel."""

    Imovel.objects.filter(pk=imovel.pk).update(
        busca=SearchVector("titulo", weight="A", config="portuguese")
        + SearchVector("descricao", weight="B", config="portuguese")
        + SearchVector("codigo", weight="A", config="portuguese")
    )


def registrar_evento(imovel, tipo, descricao, usuario=None, anterior=None, novo=None):
    return HistoricoImovel.objects.create(
        imovel=imovel,
        tipo=tipo,
        descricao=descricao,
        usuario=usuario if usuario and usuario.is_authenticated else None,
        valor_anterior=anterior,
        valor_novo=novo,
    )


def criar_imovel(dados, tenant, request=None):
    with transaction.atomic():
        imovel = Imovel(**dados, tenant=tenant, codigo=gerar_codigo(tenant))
        imovel.save()

    atualizar_indice_busca(imovel)
    registrar_evento(
        imovel,
        TipoEventoImovel.CRIACAO,
        f"Imóvel cadastrado como {imovel.get_situacao_display()}.",
        usuario=getattr(request, "user", None),
    )
    registrar(
        imovel, Acao.CRIACAO, request=request, depois=snapshot(imovel, CAMPOS_AUDITADOS)
    )
    return imovel


def atualizar_imovel(imovel, dados, request=None):
    antes = snapshot(imovel, CAMPOS_AUDITADOS)
    valor_venda_anterior = imovel.valor_venda
    valor_locacao_anterior = imovel.valor_locacao

    for campo, valor in dados.items():
        setattr(imovel, campo, valor)
    imovel.save()

    atualizar_indice_busca(imovel)
    usuario = getattr(request, "user", None)

    if imovel.valor_venda != valor_venda_anterior:
        registrar_evento(
            imovel,
            TipoEventoImovel.VALOR,
            "Valor de venda alterado.",
            usuario,
            valor_venda_anterior,
            imovel.valor_venda,
        )
    if imovel.valor_locacao != valor_locacao_anterior:
        registrar_evento(
            imovel,
            TipoEventoImovel.VALOR,
            "Valor de locação alterado.",
            usuario,
            valor_locacao_anterior,
            imovel.valor_locacao,
        )

    registrar(
        imovel,
        Acao.ALTERACAO,
        request=request,
        antes=antes,
        depois=snapshot(imovel, CAMPOS_AUDITADOS),
    )
    return imovel


def mudar_situacao(imovel, nova_situacao, request=None, motivo=""):
    """Aplica a máquina de estados. Transição inválida é recusada aqui."""

    atual = imovel.situacao

    if atual == nova_situacao:
        return imovel

    if nova_situacao not in TRANSICOES_PERMITIDAS.get(atual, set()):
        permitidas = ", ".join(sorted(TRANSICOES_PERMITIDAS.get(atual, set()))) or "nenhuma"
        raise RegraDeNegocio(
            f"Não é possível mudar de {atual} para {nova_situacao}. "
            f"Transições válidas: {permitidas}."
        )

    antes = snapshot(imovel, CAMPOS_AUDITADOS)
    imovel.situacao = nova_situacao

    # Imóvel que saiu do mercado não pode continuar anunciado.
    if nova_situacao in {
        SituacaoImovel.VENDIDO,
        SituacaoImovel.LOCADO,
        SituacaoImovel.INATIVO,
    }:
        imovel.publicado_site = False

    imovel.save(update_fields=["situacao", "publicado_site", "atualizado_em"])

    registrar_evento(
        imovel,
        TipoEventoImovel.SITUACAO,
        f"{atual} → {nova_situacao}{f' ({motivo})' if motivo else ''}.",
        usuario=getattr(request, "user", None),
    )
    registrar(
        imovel,
        Acao.ALTERACAO,
        request=request,
        antes=antes,
        depois=snapshot(imovel, CAMPOS_AUDITADOS),
    )
    return imovel


def publicar(imovel, request=None):
    """Publica no site/portais depois de validar todas as pendências."""

    pendencias = imovel.pendencias_para_publicar()
    if pendencias:
        raise RegraDeNegocio(" ".join(pendencias))

    if imovel.situacao == SituacaoImovel.EM_CAPTACAO:
        mudar_situacao(
            imovel, SituacaoImovel.DISPONIVEL, request=request, motivo="publicação"
        )

    if not imovel.disponivel_para_negocio:
        raise RegraDeNegocio(
            f"Imóvel {imovel.get_situacao_display().lower()} não pode ser publicado."
        )

    imovel.publicado_site = True
    imovel.save(update_fields=["publicado_site", "atualizado_em"])

    registrar_evento(
        imovel,
        TipoEventoImovel.PUBLICACAO,
        "Imóvel publicado no site.",
        usuario=getattr(request, "user", None),
    )
    return imovel


def despublicar(imovel, request=None, motivo=""):
    imovel.publicado_site = False
    imovel.save(update_fields=["publicado_site", "atualizado_em"])
    registrar_evento(
        imovel,
        TipoEventoImovel.DESPUBLICACAO,
        f"Imóvel despublicado{f': {motivo}' if motivo else '.'}",
        usuario=getattr(request, "user", None),
    )
    return imovel


def reordenar_fotos(imovel, ordem_ids):
    """Recebe a lista de ids na ordem desejada (drag-and-drop da ficha)."""

    fotos = {str(foto.pk): foto for foto in imovel.fotos.all()}
    desconhecidos = [i for i in ordem_ids if str(i) not in fotos]
    if desconhecidos:
        raise RegraDeNegocio("Há fotos na lista que não pertencem a este imóvel.")

    with transaction.atomic():
        for posicao, foto_id in enumerate(ordem_ids):
            foto = fotos[str(foto_id)]
            foto.ordem = posicao
            foto.capa = posicao == 0
            foto.save(update_fields=["ordem", "capa"])

    return imovel.fotos.all()


def definir_capa(imovel, foto):
    with transaction.atomic():
        imovel.fotos.update(capa=False)
        foto.capa = True
        foto.save(update_fields=["capa"])
    return foto


def exclusividades_a_vencer(tenant, dias=15):
    """Imóveis cuja exclusividade termina dentro do prazo alerta ao captador."""

    limite = timezone.localdate() + timedelta(days=dias)
    return Imovel.objects.filter(
        tenant=tenant,
        deletado_em__isnull=True,
        exclusividade_ate__isnull=False,
        exclusividade_ate__lte=limite,
        exclusividade_ate__gte=timezone.localdate(),
    )
