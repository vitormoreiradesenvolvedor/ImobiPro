from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.contratos.services import ativar_contrato
from apps.contratos.tests.factories import ContratoFactory, montar_partes
from apps.imoveis.services import publicar
from apps.locacao.models import Cobranca, StatusCobranca, StatusRepasse
from apps.locacao.services import (
    RegraDeNegocio,
    baixar_cobranca,
    calcular_encargos,
    etapa_devida,
    executar_etapa_da_regua,
    gerar_cobranca,
    gerar_repasse,
    indicadores_de_inadimplencia,
    liquidar_repasse,
    primeiro_dia,
)
from apps.pessoas.tests.factories import PessoaFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def contrato_ativo(tenant, imovel_publicavel, proprietario):
    imovel = publicar(imovel_publicavel)
    inquilino = PessoaFactory(tenant=tenant, nome="Inquilino")
    contrato = ContratoFactory(tenant=tenant, imovel=imovel)
    montar_partes(contrato, proprietario, inquilino)
    return ativar_contrato(contrato)


@pytest.fixture
def cobranca(contrato_ativo):
    return contrato_ativo.cobrancas.order_by("competencia").first()


# ---------------------------------------------------------------- geração


def test_cobranca_soma_aluguel_condominio_e_iptu(cobranca):
    # 2500 aluguel + 480 condomínio + 120 IPTU (1200 anual em 10 parcelas).
    assert cobranca.valor_aluguel == Decimal("2500.00")
    assert cobranca.valor_condominio == Decimal("480.00")
    assert cobranca.valor_iptu == Decimal("120.00")
    assert cobranca.valor_total == Decimal("3100.00")


def test_contrato_sem_condominio_nao_cobra_condominio(contrato_ativo):
    contrato_ativo.inclui_condominio = False
    contrato_ativo.save(update_fields=["inclui_condominio"])

    # A ativação já gerou as três primeiras competências, e gerar_cobranca é
    # idempotente: a competência aqui precisa ser uma que ainda não existe.
    # Com data fixa, o teste passava a depender do mês em que fosse rodado.
    competencia = primeiro_dia(timezone.localdate() + timedelta(days=365))
    nova = gerar_cobranca(contrato_ativo, competencia)

    assert nova.valor_condominio == Decimal("0.00")


def test_geracao_e_idempotente(contrato_ativo, cobranca):
    repetida = gerar_cobranca(contrato_ativo, cobranca.competencia)

    assert repetida.pk == cobranca.pk
    assert (
        Cobranca.objects.filter(
            contrato=contrato_ativo, competencia=cobranca.competencia
        ).count()
        == 1
    )


def test_vencimento_respeita_o_dia_do_contrato(cobranca):
    assert cobranca.vencimento.day == cobranca.contrato.dia_vencimento


def test_dia_de_vencimento_alto_nao_estoura_o_mes(contrato_ativo):
    contrato_ativo.dia_vencimento = 28
    contrato_ativo.save(update_fields=["dia_vencimento"])

    fevereiro = gerar_cobranca(contrato_ativo, date(2027, 2, 1))

    assert fevereiro.vencimento == date(2027, 2, 28)


def test_rotina_mensal_gera_para_contratos_ativos(contrato_ativo):
    from apps.locacao.tasks import gerar_cobrancas_mensais

    gerar_cobrancas_mensais()

    assert contrato_ativo.cobrancas.count() >= 3


# ------------------------------------------------------------------ baixa


def test_baixa_sem_atraso_nao_cobra_encargo(api_autenticada, cobranca):
    resposta = api_autenticada.post(
        reverse("cobranca-baixar", args=[cobranca.pk]),
        {"valor_pago": "3080.00", "data": cobranca.vencimento.isoformat(), "forma": "PIX"},
        format="json",
    )

    assert resposta.status_code == 200
    assert resposta.data["status"] == StatusCobranca.PAGA
    assert Decimal(resposta.data["valor_multa"]) == 0
    assert Decimal(resposta.data["valor_juros"]) == 0


def test_atraso_aplica_multa_de_2_porcento_e_juros_pro_rata(cobranca):
    dez_dias_depois = cobranca.vencimento + timedelta(days=10)

    encargos = calcular_encargos(cobranca, dez_dias_depois)

    # Multa 2% de 3100 = 62,00; juros 1%/mês por 10 dias ≈ 0,3333% = 10,33.
    assert encargos["multa"] == Decimal("62.00")
    assert encargos["juros"] == Decimal("10.33")
    assert encargos["dias_atraso"] == 10


def test_baixa_com_atraso_soma_encargos_ao_total(cobranca):
    baixar_cobranca(
        cobranca,
        Decimal("3172.33"),
        data_pagamento=cobranca.vencimento + timedelta(days=10),
    )

    cobranca.refresh_from_db()
    # 3100 + 62,00 de multa + 10,33 de juros.
    assert cobranca.valor_total == Decimal("3172.33")


def test_cobranca_ja_paga_nao_recebe_segunda_baixa(cobranca):
    valor = Decimal("3100.00")
    baixar_cobranca(cobranca, valor)

    with pytest.raises(RegraDeNegocio, match="já foi baixada"):
        baixar_cobranca(cobranca, valor)


def test_baixa_lanca_receita_no_financeiro(cobranca):
    from apps.financeiro.models import CategoriaFinanceira, Transacao

    baixar_cobranca(cobranca, Decimal("3080.00"))

    assert Transacao.objects.filter(
        cobranca=cobranca, categoria=CategoriaFinanceira.ALUGUEL
    ).exists()
    assert Transacao.objects.filter(
        cobranca=cobranca, categoria=CategoriaFinanceira.TAXA_ADMINISTRACAO
    ).exists()


# ---------------------------------------------------------------- repasse


def test_repasse_desconta_taxa_e_ignora_condominio_e_iptu(cobranca):
    """Condomínio e IPTU são de terceiros: não entram na base do repasse."""

    baixar_cobranca(cobranca, Decimal("3080.00"))
    repasse = cobranca.repasse

    assert repasse.valor_bruto == Decimal("2500.00")
    assert repasse.taxa_administracao == Decimal("200.00")  # 8% de 2500
    assert repasse.valor_liquido == Decimal("2300.00")


def test_retencao_reduz_o_liquido(api_autenticada, cobranca):
    baixar_cobranca(cobranca, Decimal("3080.00"))
    repasse = cobranca.repasse

    resposta = api_autenticada.post(
        reverse("repasse-retencoes", args=[repasse.pk]),
        {"descricao": "Troca de chuveiro", "valor": "150.00"},
        format="json",
    )

    assert Decimal(resposta.data["valor_liquido"]) == Decimal("2150.00")


def test_repasse_de_cobranca_nao_paga_nao_liquida(contrato_ativo, cobranca):
    repasse = gerar_repasse(cobranca)

    with pytest.raises(RegraDeNegocio, match="ainda não foi recebido"):
        liquidar_repasse(repasse)


def test_liquidacao_lanca_despesa_e_marca_data(api_autenticada, cobranca):
    from apps.financeiro.models import CategoriaFinanceira, Transacao

    baixar_cobranca(cobranca, Decimal("3080.00"))
    repasse = cobranca.repasse

    resposta = api_autenticada.post(reverse("repasse-liquidar", args=[repasse.pk]))

    assert resposta.data["status"] == StatusRepasse.PAGO
    assert Transacao.objects.filter(
        repasse=repasse, categoria=CategoriaFinanceira.REPASSE_PROPRIETARIO
    ).exists()


def test_repasse_pago_nao_aceita_retencao(cobranca):
    from apps.locacao.services import adicionar_retencao

    baixar_cobranca(cobranca, Decimal("3080.00"))
    repasse = cobranca.repasse
    liquidar_repasse(repasse)

    with pytest.raises(RegraDeNegocio, match="não aceita retenção"):
        adicionar_retencao(repasse, "tarde demais", 100)


# ------------------------------------------------- régua de inadimplência


def test_regua_dispara_uma_etapa_por_faixa_de_atraso(cobranca):
    cobranca.vencimento = timezone.localdate() - timedelta(days=6)
    cobranca.save(update_fields=["vencimento"])

    etapa = etapa_devida(cobranca)

    assert etapa == "COBRANCA"


def test_etapa_ja_enviada_nao_repete(cobranca):
    cobranca.vencimento = timezone.localdate() - timedelta(days=6)
    cobranca.save(update_fields=["vencimento"])
    executar_etapa_da_regua(cobranca, "COBRANCA")

    assert etapa_devida(cobranca) is None


def test_atraso_longo_pula_para_a_etapa_mais_grave(cobranca):
    """Sistema parado por 20 dias não manda "lembrete" depois do aviso formal."""

    cobranca.vencimento = timezone.localdate() - timedelta(days=16)
    cobranca.save(update_fields=["vencimento"])

    assert etapa_devida(cobranca) == "AVISO_FORMAL"

    executar_etapa_da_regua(cobranca, "AVISO_FORMAL")
    cobranca.refresh_from_db()

    # Lembrete e cobrança ficam marcados como superados, não pendentes.
    assert set(cobranca.etapas_cobranca_enviadas) == {
        "LEMBRETE",
        "COBRANCA",
        "AVISO_FORMAL",
    }
    assert etapa_devida(cobranca) is None


def test_regua_marca_cobranca_como_atrasada_e_registra_evento(cobranca):
    cobranca.vencimento = timezone.localdate() - timedelta(days=2)
    cobranca.save(update_fields=["vencimento"])

    executar_etapa_da_regua(cobranca, "LEMBRETE")

    cobranca.refresh_from_db()
    assert cobranca.status == StatusCobranca.ATRASADA
    assert cobranca.eventos.count() == 1


def test_rotina_da_regua_percorre_todas_as_cobrancas(cobranca):
    from apps.locacao.tasks import executar_regua_de_inadimplencia

    cobranca.vencimento = timezone.localdate() - timedelta(days=31)
    cobranca.save(update_fields=["vencimento"])

    assert executar_regua_de_inadimplencia() >= 1


def test_encaminhamento_juridico_notifica_a_gestao(cobranca, admin_imobiliaria):
    from apps.locacao.tasks import executar_regua_de_inadimplencia
    from apps.notificacoes.models import Notificacao

    cobranca.vencimento = timezone.localdate() - timedelta(days=31)
    cobranca.save(update_fields=["vencimento"])
    executar_regua_de_inadimplencia()

    assert Notificacao.objects.filter(tipo="COBRANCA_ATRASADA").exists()


def test_indicador_de_inadimplencia_calcula_percentual(contrato_ativo, cobranca):
    cobranca.vencimento = timezone.localdate() - timedelta(days=5)
    cobranca.save(update_fields=["vencimento"])

    dados = indicadores_de_inadimplencia(contrato_ativo.tenant, cobranca.competencia)

    assert dados["total_cobrancas"] == 1
    assert dados["atrasadas"] == 1
    assert dados["percentual"] == 100.0


def test_cobranca_de_outro_tenant_nao_aparece(api_autenticada, outro_tenant):
    from apps.imoveis.tests.factories import ImovelFactory

    alheio = ImovelFactory(
        tenant=outro_tenant, proprietario=PessoaFactory(tenant=outro_tenant)
    )
    contrato = ContratoFactory(tenant=outro_tenant, imovel=alheio)
    gerar_cobranca(contrato, timezone.localdate())

    assert api_autenticada.get(reverse("cobranca-list")).data["count"] == 0
