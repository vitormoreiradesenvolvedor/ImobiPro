"""Execução da vistoria e comparativo entrada × saída."""

from django.db import transaction
from django.utils import timezone

from apps.vistorias.models import (
    CHECKLIST_PADRAO,
    EstadoItem,
    ItemVistoria,
    StatusVistoria,
    TipoVistoria,
    Vistoria,
)


class RegraDeNegocio(Exception):
    """Erro de regra de negócio; vira 400 na API."""


@transaction.atomic
def criar_vistoria(contrato, tipo, realizada_em=None, vistoriador=None, com_checklist=True):
    from apps.contratos.models import StatusContrato

    if tipo == TipoVistoria.SAIDA and contrato.status == StatusContrato.RASCUNHO:
        raise RegraDeNegocio("Contrato em rascunho não tem vistoria de saída.")

    if Vistoria.objects.filter(contrato=contrato, tipo=tipo).exists() and tipo in {
        TipoVistoria.ENTRADA,
        TipoVistoria.SAIDA,
    }:
        raise RegraDeNegocio(f"Este contrato já tem vistoria de {tipo.lower()}.")

    vistoria = Vistoria.objects.create(
        tenant=contrato.tenant,
        contrato=contrato,
        tipo=tipo,
        realizada_em=realizada_em or timezone.localdate(),
        vistoriador=vistoriador if vistoriador and vistoriador.is_authenticated else None,
    )

    if com_checklist:
        aplicar_checklist_padrao(vistoria)

    return vistoria


def aplicar_checklist_padrao(vistoria, quartos=None):
    """Monta o roteiro com base nos cômodos do imóvel evita digitar do zero."""

    quartos = quartos if quartos is not None else (vistoria.contrato.imovel.quartos or 1)
    criados = []
    ordem = 0

    for comodo, itens in CHECKLIST_PADRAO.items():
        repeticoes = quartos if comodo == "Quarto" else 1
        for indice in range(repeticoes):
            nome_comodo = f"{comodo} {indice + 1}" if repeticoes > 1 else comodo
            for item in itens:
                criados.append(
                    ItemVistoria(
                        vistoria=vistoria,
                        comodo=nome_comodo,
                        item=item,
                        estado=EstadoItem.BOM,
                        ordem=ordem,
                    )
                )
                ordem += 1

    ItemVistoria.objects.bulk_create(criados, ignore_conflicts=True)
    return criados


def registrar_item(vistoria, comodo, item, estado, observacao="", ordem=0):
    if vistoria.status == StatusVistoria.FINALIZADA:
        raise RegraDeNegocio("Vistoria finalizada não aceita alteração.")

    registro, _ = ItemVistoria.objects.update_or_create(
        vistoria=vistoria,
        comodo=comodo,
        item=item,
        defaults={"estado": estado, "observacao": observacao, "ordem": ordem},
    )
    return registro


def finalizar_vistoria(vistoria):
    if vistoria.status == StatusVistoria.FINALIZADA:
        raise RegraDeNegocio("Esta vistoria já foi finalizada.")
    if not vistoria.itens.exists():
        raise RegraDeNegocio("Vistoria sem itens preenchidos.")

    vistoria.status = StatusVistoria.FINALIZADA
    vistoria.finalizada_em = timezone.now()
    vistoria.save(update_fields=["status", "finalizada_em"])
    return vistoria


def _linha_do_comparativo(chave, na_entrada, na_saida):
    """Uma linha do comparativo: estado antes, depois e se houve piora."""

    peso_entrada = na_entrada.peso if na_entrada else 0
    peso_saida = na_saida.peso if na_saida else 0
    variacao = peso_saida - peso_entrada

    return {
        "comodo": chave[0],
        "item": chave[1],
        "estado_entrada": na_entrada.estado if na_entrada else None,
        "estado_saida": na_saida.estado if na_saida else None,
        "observacao_entrada": na_entrada.observacao if na_entrada else "",
        "observacao_saida": na_saida.observacao if na_saida else "",
        "variacao": variacao,
        "piorou": variacao < 0,
    }


def comparativo(contrato):
    """Entrada × saída, item a item. É o que sustenta a retenção de caução."""

    entrada = contrato.vistorias.filter(tipo=TipoVistoria.ENTRADA).first()
    saida = contrato.vistorias.filter(tipo=TipoVistoria.SAIDA).first()

    if not entrada or not saida:
        raise RegraDeNegocio(
            "O comparativo exige a vistoria de entrada e a de saída finalizadas."
        )

    itens_entrada = {(item.comodo, item.item): item for item in entrada.itens.all()}
    itens_saida = {(item.comodo, item.item): item for item in saida.itens.all()}

    linhas = [
        _linha_do_comparativo(chave, itens_entrada.get(chave), itens_saida.get(chave))
        for chave in sorted(set(itens_entrada) | set(itens_saida))
    ]
    pioraram = sum(linha["piorou"] for linha in linhas)

    return {
        "contrato": contrato.numero,
        "entrada_em": entrada.realizada_em,
        "saida_em": saida.realizada_em,
        "total_itens": len(linhas),
        "itens_que_pioraram": pioraram,
        "percentual_com_avaria": (
            round(pioraram / len(linhas) * 100, 2) if linhas else 0.0
        ),
        "itens": linhas,
    }
