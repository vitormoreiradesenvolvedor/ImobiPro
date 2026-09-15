from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.contratos.services import ativar_contrato
from apps.contratos.tests.factories import ContratoFactory, montar_partes
from apps.financeiro.models import CategoriaFinanceira, TipoTransacao, Transacao
from apps.financeiro.services import RegraDeNegocio, dre, estornar, lancar
from apps.imoveis.services import publicar
from apps.locacao.services import baixar_cobranca
from apps.pessoas.tests.factories import PessoaFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def contrato_ativo(tenant, imovel_publicavel, proprietario):
    imovel = publicar(imovel_publicavel)
    contrato = ContratoFactory(tenant=tenant, imovel=imovel)
    montar_partes(contrato, proprietario, PessoaFactory(tenant=tenant))
    return ativar_contrato(contrato)


@pytest.fixture
def api_financeiro(api, financeiro):
    api.force_authenticate(user=financeiro)
    return api


def test_transacao_nao_e_deletada_pela_api(api_financeiro, tenant):
    transacao = lancar(
        tenant,
        TipoTransacao.RECEITA,
        CategoriaFinanceira.OUTRAS_RECEITAS,
        "Venda de material",
        100,
        timezone.localdate(),
    )

    resposta = api_financeiro.delete(reverse("transacao-detail", args=[transacao.pk]))

    assert resposta.status_code == 400
    assert Transacao.objects.filter(pk=transacao.pk).exists()


def test_estorno_cria_contrapartida_de_sinal_oposto(tenant):
    receita = lancar(
        tenant,
        TipoTransacao.RECEITA,
        CategoriaFinanceira.ALUGUEL,
        "Aluguel",
        2500,
        timezone.localdate(),
    )

    estorno = estornar(receita, "pagamento devolvido")

    assert estorno.tipo == TipoTransacao.DESPESA
    assert estorno.valor == receita.valor
    assert estorno.estorno_de_id == receita.pk
    assert receita.estornada is True


def test_estorno_duplicado_e_recusado(tenant):
    receita = lancar(
        tenant,
        TipoTransacao.RECEITA,
        CategoriaFinanceira.ALUGUEL,
        "Aluguel",
        2500,
        timezone.localdate(),
    )
    estornar(receita, "primeiro")

    with pytest.raises(RegraDeNegocio, match="já foi estornada"):
        estornar(receita, "segundo")


def test_dre_separa_dinheiro_de_terceiros_do_resultado(contrato_ativo, tenant):
    """Aluguel e repasse passam pela conta; só a taxa é receita da imobiliária."""

    # order_by explícito: o Meta ordena por -competencia e pegaria o mês mais distante.
    cobranca = contrato_ativo.cobrancas.order_by("competencia").first()
    baixar_cobranca(cobranca, Decimal("3100.00"))

    hoje = timezone.localdate()
    resultado = dre(tenant, hoje.replace(day=1), hoje)

    # Taxa de administração: 8% de 2500 = 200.
    assert resultado["receita_operacional"] == Decimal("200.00")
    assert resultado["volume_movimentado"] > resultado["receita_operacional"]


def test_dre_calcula_margem(tenant):
    hoje = timezone.localdate()
    lancar(
        tenant,
        TipoTransacao.RECEITA,
        CategoriaFinanceira.TAXA_ADMINISTRACAO,
        "Taxa",
        1000,
        hoje,
    )
    lancar(
        tenant, TipoTransacao.DESPESA, CategoriaFinanceira.MARKETING, "Anúncios", 250, hoje
    )

    resultado = dre(tenant, hoje.replace(day=1), hoje)

    assert resultado["resultado"] == Decimal("750.00")
    assert resultado["margem_percentual"] == 75.0


def test_estorno_zera_o_resultado_no_dre(tenant):
    hoje = timezone.localdate()
    receita = lancar(
        tenant,
        TipoTransacao.RECEITA,
        CategoriaFinanceira.TAXA_ADMINISTRACAO,
        "Taxa",
        1000,
        hoje,
    )
    estornar(receita, "erro de lançamento")

    resultado = dre(tenant, hoje.replace(day=1), hoje)

    # A receita original continua somando; o estorno entra como despesa.
    assert resultado["receita_operacional"] == Decimal("1000.00")
    assert resultado["despesa_operacional"] == Decimal("1000.00")
    assert resultado["resultado"] == Decimal("0.00")


def test_relatorio_dre_pela_api(api_financeiro, tenant):
    hoje = timezone.localdate()
    lancar(
        tenant,
        TipoTransacao.RECEITA,
        CategoriaFinanceira.TAXA_ADMINISTRACAO,
        "Taxa",
        500,
        hoje,
    )

    resposta = api_financeiro.get(reverse("relatorio", args=["dre"]))

    assert resposta.status_code == 200
    assert Decimal(resposta.data["receita_operacional"]) == Decimal("500.00")


def test_periodo_invertido_e_recusado(api_financeiro):
    hoje = timezone.localdate()
    resposta = api_financeiro.get(
        reverse("relatorio", args=["dre"]),
        {"inicio": hoje.isoformat(), "fim": (hoje - timedelta(days=5)).isoformat()},
    )

    assert resposta.status_code == 400


def test_relatorio_inexistente_retorna_400(api_financeiro):
    assert api_financeiro.get(reverse("relatorio", args=["inventado"])).status_code == 400


def test_corretor_nao_acessa_o_financeiro(api, corretor):
    api.force_authenticate(user=corretor)

    assert api.get(reverse("transacao-list")).status_code == 403
    assert api.get(reverse("relatorio", args=["dre"])).status_code == 403


def test_resumo_do_dashboard_reune_os_numeros(api_financeiro, contrato_ativo):
    resposta = api_financeiro.get(reverse("resumo-financeiro"))

    assert resposta.status_code == 200
    assert "a_receber" in resposta.data
    assert "inadimplencia" in resposta.data


def test_desempenho_de_corretores(api_financeiro, tenant, corretor):
    from apps.crm.tests.factories import LeadFactory

    LeadFactory(tenant=tenant, corretor=corretor, estagio="FECHADO_GANHO")
    LeadFactory(
        tenant=tenant, corretor=corretor, estagio="FECHADO_PERDIDO", motivo_perda="PRECO"
    )

    resposta = api_financeiro.get(reverse("relatorio", args=["desempenho-corretores"]))

    linha = next(
        linha for linha in resposta.data if linha["corretor"] == corretor.nome_completo
    )
    assert linha["leads"] == 2
    assert linha["ganhos"] == 1
    assert linha["conversao"] == 50.0


# --------------------------------------------------------- conciliação CNAB


def linha_cnab(nosso_numero, valor_centavos, data="150826", ocorrencia="06"):
    """Monta um registro tipo 1 de 400 posições com os campos que lemos."""

    linha = list(" " * 400)
    linha[0] = "1"
    linha[62:73] = list(nosso_numero.rjust(11, "0"))
    linha[108:110] = list(ocorrencia)
    linha[110:116] = list(data)
    linha[253:266] = list(str(valor_centavos).rjust(13, "0"))
    return "".join(linha)


def test_conciliacao_baixa_a_cobranca_correspondente(api_financeiro, contrato_ativo):
    from django.core.files.uploadedfile import SimpleUploadedFile

    # order_by explícito: o Meta ordena por -competencia e pegaria o mês mais distante.
    cobranca = contrato_ativo.cobrancas.order_by("competencia").first()
    cobranca.nosso_numero = "00000012345"
    cobranca.save(update_fields=["nosso_numero"])

    arquivo = SimpleUploadedFile(
        "retorno.ret",
        linha_cnab("12345", 310000).encode("latin-1"),
        content_type="text/plain",
    )

    resposta = api_financeiro.post(
        reverse("conciliar"), {"arquivo": arquivo}, format="multipart"
    )

    assert resposta.status_code == 200
    assert resposta.data["total_conciliado"] == 1
    cobranca.refresh_from_db()
    assert cobranca.status == "PAGA"
    assert cobranca.valor_pago == Decimal("3100.00")


def test_retorno_do_banco_casa_com_a_cobranca_recem_gerada(api_financeiro, contrato_ativo):
    """Sem intervenção manual: a cobrança já nasce com o "nosso número".

    O parser lê 11 posições do arquivo; se a geração não preenchesse o campo,
    a conciliação nunca acharia a cobrança e a baixa em lote seria inútil.
    """

    from django.core.files.uploadedfile import SimpleUploadedFile

    cobranca = contrato_ativo.cobrancas.order_by("competencia").first()
    assert cobranca.nosso_numero, "cobrança gerada sem nosso número"
    assert len(cobranca.nosso_numero) <= 11

    arquivo = SimpleUploadedFile(
        "retorno.ret",
        linha_cnab(cobranca.nosso_numero, 310000).encode("latin-1"),
        content_type="text/plain",
    )

    resposta = api_financeiro.post(
        reverse("conciliar"), {"arquivo": arquivo}, format="multipart"
    )

    assert resposta.status_code == 200
    assert resposta.data["total_conciliado"] == 1
    cobranca.refresh_from_db()
    assert cobranca.status == "PAGA"


def test_conciliacao_reporta_linha_sem_correspondencia(api_financeiro, contrato_ativo):
    from django.core.files.uploadedfile import SimpleUploadedFile

    arquivo = SimpleUploadedFile(
        "retorno.ret",
        linha_cnab("99999", 100000).encode("latin-1"),
        content_type="text/plain",
    )

    resposta = api_financeiro.post(
        reverse("conciliar"), {"arquivo": arquivo}, format="multipart"
    )

    assert resposta.data["total_conciliado"] == 0
    assert len(resposta.data["nao_encontradas"]) == 1


def test_conciliacao_ignora_ocorrencia_que_nao_e_liquidacao(api_financeiro, contrato_ativo):
    from django.core.files.uploadedfile import SimpleUploadedFile

    # order_by explícito: o Meta ordena por -competencia e pegaria o mês mais distante.
    cobranca = contrato_ativo.cobrancas.order_by("competencia").first()
    cobranca.nosso_numero = "00000012345"
    cobranca.save(update_fields=["nosso_numero"])

    arquivo = SimpleUploadedFile(
        "retorno.ret",
        linha_cnab("12345", 310000, ocorrencia="03").encode("latin-1"),
        content_type="text/plain",
    )

    resposta = api_financeiro.post(
        reverse("conciliar"), {"arquivo": arquivo}, format="multipart"
    )

    assert resposta.data["total_conciliado"] == 0
    cobranca.refresh_from_db()
    assert cobranca.status != "PAGA"
