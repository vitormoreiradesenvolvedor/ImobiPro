import pytest
from django.urls import reverse

from apps.contratos.services import ativar_contrato
from apps.contratos.tests.factories import ContratoFactory, montar_partes
from apps.imoveis.services import publicar
from apps.imoveis.tests.factories import imagem_de_teste
from apps.pessoas.tests.factories import PessoaFactory
from apps.vistorias.models import StatusVistoria, TipoVistoria
from apps.vistorias.services import (
    RegraDeNegocio,
    comparativo,
    criar_vistoria,
    finalizar_vistoria,
    registrar_item,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def contrato_ativo(tenant, imovel_publicavel, proprietario):
    imovel = publicar(imovel_publicavel)
    contrato = ContratoFactory(tenant=tenant, imovel=imovel)
    montar_partes(contrato, proprietario, PessoaFactory(tenant=tenant))
    return ativar_contrato(contrato)


def test_vistoria_nasce_com_checklist_do_imovel(api_autenticada, contrato_ativo):
    resposta = api_autenticada.post(
        reverse("vistoria-list"),
        {"contrato": str(contrato_ativo.pk), "tipo": "ENTRADA"},
        format="json",
    )

    assert resposta.status_code == 201
    # 2 quartos no imóvel ⇒ o checklist replica o cômodo "Quarto".
    comodos = {item["comodo"] for item in resposta.data["itens"]}
    assert "Quarto 1" in comodos
    assert "Quarto 2" in comodos
    assert resposta.data["status"] == StatusVistoria.RASCUNHO


def test_entrada_duplicada_e_recusada(contrato_ativo):
    criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA)

    with pytest.raises(RegraDeNegocio, match="já tem vistoria"):
        criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA)


def test_periodica_pode_repetir(contrato_ativo):
    criar_vistoria(contrato_ativo, TipoVistoria.PERIODICA, com_checklist=False)
    criar_vistoria(contrato_ativo, TipoVistoria.PERIODICA, com_checklist=False)

    assert contrato_ativo.vistorias.filter(tipo=TipoVistoria.PERIODICA).count() == 2


def test_item_com_foto_pelo_celular(api_autenticada, contrato_ativo):
    vistoria = criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA, com_checklist=False)

    resposta = api_autenticada.post(
        reverse("vistoria-itens", args=[vistoria.pk]),
        {
            "comodo": "Cozinha",
            "item": "Pia",
            "estado": "REGULAR",
            "observacao": "Sifão com vazamento leve",
            "fotos": [imagem_de_teste("pia1.png"), imagem_de_teste("pia2.png")],
        },
        format="multipart",
    )

    assert resposta.status_code == 201
    assert len(resposta.data["fotos"]) == 2


def test_reenviar_o_mesmo_item_atualiza_em_vez_de_duplicar(contrato_ativo):
    vistoria = criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA, com_checklist=False)

    registrar_item(vistoria, "Sala", "Piso", "BOM")
    registrar_item(vistoria, "Sala", "Piso", "RUIM", "risco profundo")

    assert vistoria.itens.count() == 1
    assert vistoria.itens.first().estado == "RUIM"


def test_vistoria_finalizada_nao_aceita_alteracao(contrato_ativo):
    vistoria = criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA)
    finalizar_vistoria(vistoria)

    with pytest.raises(RegraDeNegocio, match="não aceita alteração"):
        registrar_item(vistoria, "Sala", "Piso", "BOM")


def test_vistoria_sem_item_nao_finaliza(contrato_ativo):
    vistoria = criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA, com_checklist=False)

    with pytest.raises(RegraDeNegocio, match="sem itens"):
        finalizar_vistoria(vistoria)


def test_assinaturas_sao_registradas(api_autenticada, contrato_ativo):
    vistoria = criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA)
    finalizar_vistoria(vistoria)

    resposta = api_autenticada.post(
        reverse("vistoria-assinar", args=[vistoria.pk]),
        {"locatario": True, "imobiliaria": True},
        format="json",
    )

    assert resposta.data["assinada"] is True


def test_contador_de_itens_com_problema(contrato_ativo):
    vistoria = criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA, com_checklist=False)
    registrar_item(vistoria, "Sala", "Piso", "BOM")
    registrar_item(vistoria, "Sala", "Parede", "RUIM")
    registrar_item(vistoria, "Cozinha", "Torneira", "AUSENTE")

    assert vistoria.itens_com_problema == 2


# ------------------------------------------------------------- comparativo


def test_comparativo_exige_entrada_e_saida(contrato_ativo):
    criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA)

    with pytest.raises(RegraDeNegocio, match="entrada e a de saída"):
        comparativo(contrato_ativo)


def test_comparativo_aponta_o_que_piorou(api_autenticada, contrato_ativo):
    entrada = criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA, com_checklist=False)
    registrar_item(entrada, "Sala", "Piso", "OTIMO")
    registrar_item(entrada, "Sala", "Parede", "BOM")
    registrar_item(entrada, "Cozinha", "Torneira", "BOM")
    finalizar_vistoria(entrada)

    saida = criar_vistoria(contrato_ativo, TipoVistoria.SAIDA, com_checklist=False)
    registrar_item(saida, "Sala", "Piso", "RUIM", "manchas de infiltração")
    registrar_item(saida, "Sala", "Parede", "BOM")
    registrar_item(saida, "Cozinha", "Torneira", "AUSENTE")
    finalizar_vistoria(saida)

    resposta = api_autenticada.get(
        reverse("vistoria-comparativo", args=[contrato_ativo.pk])
    )

    assert resposta.status_code == 200
    assert resposta.data["total_itens"] == 3
    assert resposta.data["itens_que_pioraram"] == 2

    piso = next(i for i in resposta.data["itens"] if i["item"] == "Piso")
    assert piso["estado_entrada"] == "OTIMO"
    assert piso["estado_saida"] == "RUIM"
    assert piso["piorou"] is True

    parede = next(i for i in resposta.data["itens"] if i["item"] == "Parede")
    assert parede["piorou"] is False


def test_item_que_melhorou_nao_conta_como_avaria(contrato_ativo):
    entrada = criar_vistoria(contrato_ativo, TipoVistoria.ENTRADA, com_checklist=False)
    registrar_item(entrada, "Sala", "Pintura", "RUIM")
    finalizar_vistoria(entrada)

    saida = criar_vistoria(contrato_ativo, TipoVistoria.SAIDA, com_checklist=False)
    registrar_item(saida, "Sala", "Pintura", "OTIMO")
    finalizar_vistoria(saida)

    resultado = comparativo(contrato_ativo)

    assert resultado["itens_que_pioraram"] == 0
    assert resultado["percentual_com_avaria"] == 0.0


def test_vistoria_de_outro_tenant_nao_aparece(api_autenticada, outro_tenant):
    from apps.imoveis.tests.factories import ImovelFactory

    alheio = ImovelFactory(
        tenant=outro_tenant, proprietario=PessoaFactory(tenant=outro_tenant)
    )
    contrato = ContratoFactory(tenant=outro_tenant, imovel=alheio)
    criar_vistoria(contrato, TipoVistoria.PERIODICA, com_checklist=False)

    assert api_autenticada.get(reverse("vistoria-list")).data["count"] == 0
