from datetime import timedelta
from decimal import Decimal

import pytest
from django.db.utils import IntegrityError
from django.urls import reverse
from django.utils import timezone

from apps.contratos.models import (
    Contrato,
    PapelComissao,
    StatusComissao,
    StatusContrato,
    TipoContrato,
)
from apps.contratos.services import (
    RegraDeNegocio,
    adicionar_parte,
    aplicar_reajuste,
    ativar_contrato,
    calcular_multa_rescisoria,
    criar_contrato,
    rescindir_contrato,
)
from apps.contratos.tests.factories import ContratoFactory, montar_partes
from apps.imoveis.models import SituacaoImovel
from apps.imoveis.services import publicar
from apps.pessoas.tests.factories import PessoaFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def imovel_disponivel(imovel_publicavel):
    return publicar(imovel_publicavel)


@pytest.fixture
def inquilino(tenant):
    return PessoaFactory(tenant=tenant, nome="Inquilino Teste")


@pytest.fixture
def contrato_pronto(tenant, imovel_disponivel, proprietario, inquilino):
    contrato = ContratoFactory(tenant=tenant, imovel=imovel_disponivel)
    return montar_partes(contrato, proprietario, inquilino)


def payload_contrato(imovel):
    return {
        "tipo": "LOCACAO",
        "imovel": str(imovel.pk),
        "data_inicio": timezone.localdate().isoformat(),
        "data_fim": (timezone.localdate() + timedelta(days=900)).isoformat(),
        "valor": "2500.00",
        "dia_vencimento": 10,
        "taxa_administracao_percent": "8.00",
    }


# ------------------------------------------------------------------ criação


def test_numeracao_por_tipo_e_ano(api_autenticada, imovel_disponivel, tenant):
    primeiro = api_autenticada.post(
        reverse("contrato-list"), payload_contrato(imovel_disponivel), format="json"
    )
    ano = timezone.localdate().year

    assert primeiro.data["numero"] == f"LOC-{ano}-0001"
    assert primeiro.data["status"] == StatusContrato.RASCUNHO


def test_locacao_sem_data_fim_e_recusada(tenant, imovel_disponivel):
    dados = {
        "tipo": TipoContrato.LOCACAO,
        "imovel": imovel_disponivel,
        "data_inicio": timezone.localdate(),
        "valor": Decimal("2500"),
    }

    with pytest.raises(RegraDeNegocio, match="data de término"):
        criar_contrato(dados, tenant)


def test_data_fim_anterior_ao_inicio_e_recusada(api_autenticada, imovel_disponivel):
    payload = payload_contrato(imovel_disponivel)
    payload["data_fim"] = (timezone.localdate() - timedelta(days=1)).isoformat()

    resposta = api_autenticada.post(reverse("contrato-list"), payload, format="json")

    assert resposta.status_code == 400
    assert "data_fim" in resposta.data["campos"]


def test_dia_de_vencimento_acima_de_28_e_recusado(api_autenticada, imovel_disponivel):
    payload = {**payload_contrato(imovel_disponivel), "dia_vencimento": 31}

    resposta = api_autenticada.post(reverse("contrato-list"), payload, format="json")

    assert resposta.status_code == 400


def test_papel_incompativel_com_o_tipo_e_recusado(contrato_pronto, tenant):
    comprador = PessoaFactory(tenant=tenant)

    with pytest.raises(RegraDeNegocio, match="não se aplica"):
        adicionar_parte(contrato_pronto, comprador, "COMPRADOR")


def test_pessoa_de_outro_tenant_nao_vira_parte(contrato_pronto, outro_tenant):
    forasteiro = PessoaFactory(tenant=outro_tenant)

    with pytest.raises(RegraDeNegocio, match="não pertence"):
        adicionar_parte(contrato_pronto, forasteiro, "FIADOR")


# ----------------------------------------------------------------- ativação


def test_ativacao_lista_pendencias(api_autenticada, tenant, imovel_disponivel):
    contrato = ContratoFactory(tenant=tenant, imovel=imovel_disponivel)

    resposta = api_autenticada.post(reverse("contrato-ativar", args=[contrato.pk]))

    assert resposta.status_code == 400
    assert "locador" in str(resposta.data["campos"]["ativacao"]).lower()


def test_ativacao_marca_imovel_como_locado(api_autenticada, contrato_pronto):
    resposta = api_autenticada.post(reverse("contrato-ativar", args=[contrato_pronto.pk]))

    assert resposta.status_code == 200
    assert resposta.data["status"] == StatusContrato.ATIVO
    contrato_pronto.imovel.refresh_from_db()
    assert contrato_pronto.imovel.situacao == SituacaoImovel.LOCADO


def test_resposta_da_ativacao_ja_traz_as_comissoes(api_autenticada, contrato_pronto):
    """A tela mostra as comissões sem precisar recarregar.

    O contrato é carregado com prefetch antes de a ativação criar as comissões;
    sem reler do banco, a resposta viria com a lista vazia.
    """

    resposta = api_autenticada.post(reverse("contrato-ativar", args=[contrato_pronto.pk]))

    assert resposta.status_code == 200
    assert resposta.data["comissoes"], "resposta da ativação veio sem comissões"


def test_ativacao_gera_cobrancas_dos_proximos_meses(contrato_pronto):
    ativar_contrato(contrato_pronto)

    assert contrato_pronto.cobrancas.count() == 3


def test_contrato_ativo_nao_e_editado(api_autenticada, contrato_pronto):
    ativar_contrato(contrato_pronto)

    resposta = api_autenticada.patch(
        reverse("contrato-detail", args=[contrato_pronto.pk]),
        {"valor": "9999.00"},
        format="json",
    )

    assert resposta.status_code == 400


def test_locacoes_sobrepostas_no_mesmo_imovel_sao_barradas_pelo_banco(
    contrato_pronto, tenant, proprietario, inquilino
):
    """A trava é do PostgreSQL: nem duas requisições simultâneas passam."""

    ativar_contrato(contrato_pronto)

    concorrente = ContratoFactory(
        tenant=tenant,
        imovel=contrato_pronto.imovel,
        data_inicio=timezone.localdate() + timedelta(days=30),
        data_fim=timezone.localdate() + timedelta(days=800),
    )
    montar_partes(concorrente, proprietario, inquilino)

    sobreposto = Contrato.objects.filter(pk=concorrente.pk)

    with pytest.raises(IntegrityError):
        sobreposto.update(status=StatusContrato.ATIVO)


# ---------------------------------------------------------------- comissões


def test_comissao_de_venda_e_rateada_conforme_a_tabela(
    api_autenticada, tenant, imovel_disponivel, proprietario, corretor
):
    comprador = PessoaFactory(tenant=tenant)
    contrato = ContratoFactory(
        tenant=tenant,
        imovel=imovel_disponivel,
        tipo=TipoContrato.VENDA,
        numero="VEN-2026-0001",
        valor="500000.00",
        data_fim=None,
    )
    adicionar_parte(contrato, proprietario, "VENDEDOR")
    adicionar_parte(contrato, comprador, "COMPRADOR")

    ativar_contrato(contrato)

    comissoes = {c.papel: c for c in contrato.comissoes.all()}
    # 6% de 500.000 = 30.000, rateados 40/40/20.
    assert comissoes[PapelComissao.CAPTADOR].valor == Decimal("12000.00")
    assert comissoes[PapelComissao.VENDEDOR].valor == Decimal("12000.00")
    assert comissoes[PapelComissao.IMOBILIARIA].valor == Decimal("6000.00")
    assert sum(c.valor for c in comissoes.values()) == Decimal("30000.00")


def test_comissao_congela_o_percentual_do_fechamento(
    api_autenticada, tenant, contrato_pronto
):
    from apps.contratos.services import configuracao_comissao

    ativar_contrato(contrato_pronto)
    valor_original = contrato_pronto.comissoes.first().valor

    config = configuracao_comissao(tenant)
    config.percentual_venda = 10
    config.save()

    contrato_pronto.comissoes.first().refresh_from_db()
    assert contrato_pronto.comissoes.first().valor == valor_original


def test_comissao_so_e_liberada_com_contrato_ativo(api_autenticada, contrato_pronto):
    from apps.contratos.services import gerar_comissoes, liberar_comissao

    comissao = gerar_comissoes(contrato_pronto)[0]

    with pytest.raises(RegraDeNegocio, match="contrato ativo"):
        liberar_comissao(comissao)


def test_pagamento_de_comissao_lanca_despesa(api_autenticada, contrato_pronto):
    from apps.financeiro.models import CategoriaFinanceira, Transacao

    ativar_contrato(contrato_pronto)
    comissao = contrato_pronto.comissoes.exclude(papel=PapelComissao.IMOBILIARIA).first()

    api_autenticada.post(reverse("comissao-liberar", args=[comissao.pk]))
    api_autenticada.post(reverse("comissao-pagar", args=[comissao.pk]))

    assert Transacao.objects.filter(
        comissao=comissao, categoria=CategoriaFinanceira.FOLHA
    ).exists()


def test_corretor_so_ve_a_propria_comissao(api, tenant, contrato_pronto, corretor):
    from apps.accounts.tests.factories import UsuarioFactory

    ativar_contrato(contrato_pronto)
    contrato_pronto.comissoes.update(usuario=UsuarioFactory(tenant=tenant))
    api.force_authenticate(user=corretor)

    assert api.get(reverse("comissao-list")).data["count"] == 0


def test_rateio_que_nao_soma_cem_e_recusado(api_autenticada):
    resposta = api_autenticada.post(
        reverse("config-comissao-list"),
        {"rateio_captador": "50", "rateio_vendedor": "40", "rateio_imobiliaria": "20"},
        format="json",
    )

    assert resposta.status_code == 400
    assert "100%" in str(resposta.data["campos"])


# ----------------------------------------------------------------- reajuste


def test_previa_de_reajuste_nao_grava(api_autenticada, contrato_pronto):
    ativar_contrato(contrato_pronto)

    resposta = api_autenticada.post(
        reverse("contrato-reajustar", args=[contrato_pronto.pk]),
        {"percentual": "5.000"},
        format="json",
    )

    assert resposta.status_code == 200
    assert Decimal(resposta.data["valor_novo"]) == Decimal("2625.00")
    contrato_pronto.refresh_from_db()
    assert contrato_pronto.valor == Decimal("2500.00")  # nada mudou


def test_reajuste_aplicado_altera_valor_e_gera_historico(api_autenticada, contrato_pronto):
    ativar_contrato(contrato_pronto)

    resposta = api_autenticada.post(
        reverse("contrato-reajustar", args=[contrato_pronto.pk]),
        {"percentual": "5.000", "aplicar": True},
        format="json",
    )

    assert resposta.status_code == 201
    contrato_pronto.refresh_from_db()
    assert contrato_pronto.valor == Decimal("2625.00")
    assert contrato_pronto.reajustes.count() == 1


def test_contrato_sem_reajuste_recusa_a_operacao(contrato_pronto):
    contrato_pronto.indice_reajuste = "SEM_REAJUSTE"
    contrato_pronto.save(update_fields=["indice_reajuste"])
    ativar_contrato(contrato_pronto)

    with pytest.raises(RegraDeNegocio, match="sem reajuste"):
        aplicar_reajuste(contrato_pronto, 5)


def test_proximo_reajuste_conta_12_meses(contrato_pronto):
    ativar_contrato(contrato_pronto)

    esperado = contrato_pronto.data_inicio + timedelta(days=365)
    assert contrato_pronto.proximo_reajuste_em == esperado


# ----------------------------------------------------------------- rescisão


def test_multa_rescisoria_e_proporcional_ao_prazo_restante(contrato_pronto):
    """Metade do contrato cumprida = metade da multa cheia."""

    ativar_contrato(contrato_pronto)
    meio = contrato_pronto.data_inicio + timedelta(days=450)

    multa = calcular_multa_rescisoria(contrato_pronto, meio)

    # Multa cheia = 3 × 2500 = 7500; metade do prazo restante ⇒ ~3750.
    assert Decimal("3700") < multa < Decimal("3800")


def test_rescisao_no_fim_do_prazo_nao_tem_multa(contrato_pronto):
    ativar_contrato(contrato_pronto)

    assert calcular_multa_rescisoria(contrato_pronto, contrato_pronto.data_fim) == 0


def test_rescisao_devolve_imovel_ao_mercado(api_autenticada, contrato_pronto):
    ativar_contrato(contrato_pronto)

    resposta = api_autenticada.post(
        reverse("contrato-rescindir", args=[contrato_pronto.pk]),
        {"motivo": "mudança de cidade"},
        format="json",
    )

    assert resposta.status_code == 200
    contrato_pronto.imovel.refresh_from_db()
    assert contrato_pronto.imovel.situacao == SituacaoImovel.DISPONIVEL


def test_rescisao_cancela_cobrancas_futuras_e_comissoes_previstas(contrato_pronto):
    from apps.locacao.models import StatusCobranca

    ativar_contrato(contrato_pronto)
    rescindir_contrato(contrato_pronto, "inadimplência")

    assert not contrato_pronto.cobrancas.filter(
        status=StatusCobranca.ABERTA, vencimento__gt=timezone.localdate()
    ).exists()
    assert not contrato_pronto.comissoes.filter(status=StatusComissao.PREVISTA).exists()


def test_rascunho_nao_pode_ser_rescindido(contrato_pronto):
    with pytest.raises(RegraDeNegocio, match="ativo"):
        rescindir_contrato(contrato_pronto, "qualquer")


def test_contratos_a_vencer_filtra_pela_janela(api_autenticada, contrato_pronto):
    ativar_contrato(contrato_pronto)
    contrato_pronto.data_fim = timezone.localdate() + timedelta(days=45)
    contrato_pronto.save(update_fields=["data_fim"])

    resposta = api_autenticada.get(reverse("contrato-list"), {"vencendo_em": 90})

    assert resposta.data["count"] == 1


def test_contrato_de_outro_tenant_nao_aparece(api_autenticada, outro_tenant):
    from apps.imoveis.tests.factories import ImovelFactory

    alheio = ImovelFactory(
        tenant=outro_tenant, proprietario=PessoaFactory(tenant=outro_tenant)
    )
    ContratoFactory(tenant=outro_tenant, imovel=alheio)

    assert api_autenticada.get(reverse("contrato-list")).data["count"] == 0
