"""Portal do cliente: o inquilino vê o contrato dele e nada além disso.

O risco aqui não é a tela ficar feia; é devolver dado de outra pessoa. Por isso
metade destes testes é sobre o que o portal recusa.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import Papel, Usuario
from apps.contratos.services import ativar_contrato
from apps.locacao.models import Cobranca

pytestmark = pytest.mark.django_db

SENHA = "senha-de-teste-123"


@pytest.fixture
def contrato_ativo(contrato_pronto):
    ativar_contrato(contrato_pronto)
    contrato_pronto.refresh_from_db()
    return contrato_pronto


@pytest.fixture
def inquilino(contrato_ativo, tenant):
    """Acesso do locatário, como a imobiliária cria depois da assinatura."""

    parte = contrato_ativo.partes.get(papel="LOCATARIO")
    pessoa = parte.pessoa
    pessoa.email = "locatario@teste.local"
    pessoa.save(update_fields=["email"])

    return Usuario.objects.create_user(
        email=pessoa.email,
        password=SENHA,
        nome_completo=pessoa.nome,
        papel=Papel.INQUILINO,
        tenant=tenant,
        pessoa=pessoa,
    )


@pytest.fixture
def api_inquilino(api, inquilino):
    api.force_authenticate(inquilino)
    return api


# ------------------------------------------------------------------- o que vê


def test_resumo_mostra_o_contrato_do_cliente(api_inquilino, contrato_ativo):
    resposta = api_inquilino.get(reverse("meu-resumo"))

    assert resposta.status_code == 200
    assert resposta.data["contratos_ativos"] == 1
    assert resposta.data["contrato_atual"]["numero"] == contrato_ativo.numero
    assert resposta.data["contrato_atual"]["papel_no_contrato"] == "Locatário"


def test_cobrancas_sao_as_do_proprio_contrato(api_inquilino, contrato_ativo):
    resposta = api_inquilino.get(reverse("minha-cobranca-list"))

    assert resposta.status_code == 200
    assert resposta.data["count"] == contrato_ativo.cobrancas.count()


def test_proxima_cobranca_e_a_mais_perto_de_vencer(api_inquilino, contrato_ativo):
    resposta = api_inquilino.get(reverse("meu-resumo"))

    proxima = resposta.data["proxima_cobranca"]
    primeira = contrato_ativo.cobrancas.order_by("vencimento").first()
    assert proxima["competencia"] == primeira.competencia.isoformat()


def test_segunda_via_do_contrato_sai_em_pdf(api_inquilino, contrato_ativo):
    resposta = api_inquilino.get(
        reverse("meu-contrato-pdf", kwargs={"contrato_id": contrato_ativo.id})
    )

    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "application/pdf"


# --------------------------------------------------------------- o que recusa


def test_inquilino_nao_entra_no_painel_da_imobiliaria(api_inquilino):
    """Estar autenticado no tenant não pode dar acesso à carteira inteira."""

    for rota in ["imovel-list", "pessoa-list", "contrato-list", "cobranca-list"]:
        resposta = api_inquilino.get(reverse(rota))
        assert resposta.status_code == 403, rota


def test_contrato_de_outra_pessoa_nao_aparece(api_inquilino, tenant, contrato_ativo):
    """Trocar o id na URL não pode revelar contrato alheio."""

    from apps.contratos.tests.factories import ContratoFactory
    from apps.imoveis.tests.factories import ImovelFactory
    from apps.pessoas.tests.factories import PessoaFactory

    alheio = ContratoFactory(
        tenant=tenant,
        imovel=ImovelFactory(tenant=tenant, proprietario=PessoaFactory(tenant=tenant)),
    )

    resposta = api_inquilino.get(
        reverse("meu-contrato-pdf", kwargs={"contrato_id": alheio.id})
    )

    assert resposta.status_code == 404


def test_cobranca_de_outro_contrato_nao_vaza(api_inquilino, tenant, contrato_ativo):
    from apps.contratos.tests.factories import ContratoFactory
    from apps.imoveis.tests.factories import ImovelFactory
    from apps.pessoas.tests.factories import PessoaFactory

    outro = ContratoFactory(
        tenant=tenant,
        imovel=ImovelFactory(tenant=tenant, proprietario=PessoaFactory(tenant=tenant)),
    )
    Cobranca.objects.create(
        tenant=tenant,
        contrato=outro,
        competencia="2026-09-01",
        vencimento="2026-09-10",
        valor_aluguel=Decimal("1000.00"),
        valor_total=Decimal("1000.00"),
    )

    resposta = api_inquilino.get(reverse("minha-cobranca-list"))

    numeros = {linha["contrato_numero"] for linha in resposta.data["results"]}
    assert numeros == {contrato_ativo.numero}


def test_acesso_sem_cadastro_vinculado_e_recusado(api, tenant):
    """Sem vínculo com a pessoa não há como saber o que é dele."""

    solto = Usuario.objects.create_user(
        email="solto@teste.local",
        password=SENHA,
        nome_completo="Sem Vínculo",
        papel=Papel.INQUILINO,
        tenant=tenant,
    )
    api.force_authenticate(solto)

    assert api.get(reverse("meu-resumo")).status_code == 403


def test_equipe_da_imobiliaria_nao_usa_o_portal(api_autenticada):
    assert api_autenticada.get(reverse("meu-resumo")).status_code == 403


# ------------------------------------------------------------------- chamados


def test_inquilino_abre_chamado_de_manutencao(api_inquilino, contrato_ativo):
    resposta = api_inquilino.post(
        reverse("meu-chamado-list"),
        {"mensagem": "O chuveiro parou de esquentar."},
        format="json",
    )

    assert resposta.status_code == 201
    assert resposta.data["protocolo"].startswith("ATD-")
    assert resposta.data["tipo"] == "MANUTENCAO"


def test_chamado_aparece_na_lista_do_cliente(api_inquilino, contrato_ativo):
    api_inquilino.post(
        reverse("meu-chamado-list"), {"mensagem": "Infiltração na parede."}, format="json"
    )

    resposta = api_inquilino.get(reverse("meu-chamado-list"))

    assert resposta.data["count"] == 1
    assert "Infiltração" in resposta.data["results"][0]["mensagem"]


def test_sem_contrato_ativo_nao_abre_chamado(api, tenant, contrato_pronto):
    """Quem não mora mais lá não abre chamado de manutenção."""

    parte = contrato_pronto.partes.get(papel="LOCATARIO")
    pessoa = parte.pessoa
    pessoa.email = "exlocatario@teste.local"
    pessoa.save(update_fields=["email"])
    usuario = Usuario.objects.create_user(
        email=pessoa.email,
        password=SENHA,
        nome_completo=pessoa.nome,
        papel=Papel.INQUILINO,
        tenant=tenant,
        pessoa=pessoa,
    )
    api.force_authenticate(usuario)

    resposta = api.post(
        reverse("meu-chamado-list"), {"mensagem": "Torneira pingando."}, format="json"
    )

    assert resposta.status_code == 400


# ------------------------------------------------------- criação do acesso


def test_imobiliaria_cria_o_acesso_depois_de_assinar(api_autenticada, contrato_ativo):
    parte = contrato_ativo.partes.get(papel="LOCATARIO")
    parte.pessoa.email = "novoacesso@teste.local"
    parte.pessoa.save(update_fields=["email"])

    resposta = api_autenticada.post(
        reverse("contrato-acesso-do-inquilino", args=[contrato_ativo.id])
    )

    assert resposta.status_code == 201
    assert resposta.data["senha_provisoria"]
    criado = Usuario.objects.get(email="novoacesso@teste.local")
    assert criado.papel == Papel.INQUILINO
    assert criado.pessoa == parte.pessoa


def test_contrato_em_rascunho_nao_libera_portal(api_autenticada, contrato_pronto):
    resposta = api_autenticada.post(
        reverse("contrato-acesso-do-inquilino", args=[contrato_pronto.id])
    )

    assert resposta.status_code == 400
    assert "ativo" in str(resposta.data["campos"]).lower()


def test_locatario_sem_email_avisa_qual_cadastro_corrigir(api_autenticada, contrato_ativo):
    parte = contrato_ativo.partes.get(papel="LOCATARIO")
    parte.pessoa.email = ""
    parte.pessoa.save(update_fields=["email"])

    resposta = api_autenticada.post(
        reverse("contrato-acesso-do-inquilino", args=[contrato_ativo.id])
    )

    assert resposta.status_code == 400
    assert parte.pessoa.nome in str(resposta.data["campos"])
