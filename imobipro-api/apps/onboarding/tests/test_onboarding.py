import pytest
from django.urls import reverse

from apps.crm.tests.factories import LeadFactory
from apps.imoveis.services import publicar
from apps.imoveis.tests.factories import ImovelFactory
from apps.onboarding.models import ProgressoOnboarding
from apps.pessoas.tests.factories import PessoaFactory

pytestmark = pytest.mark.django_db


def missao(dados, chave):
    return next(m for m in dados["missoes"] if m["chave"] == chave)


def test_usuario_novo_comeca_zerado(api_autenticada):
    dados = api_autenticada.get(reverse("onboarding")).data

    assert dados["pontos"] == 0
    assert dados["percentual"] == 0
    assert dados["nivel"] == "Começando"
    assert dados["concluido"] is False
    assert missao(dados, "cadastrar_pessoa")["proxima"] is True


def test_missao_e_conferida_contra_dado_real(api_autenticada, tenant):
    antes = api_autenticada.get(reverse("onboarding")).data
    assert missao(antes, "cadastrar_pessoa")["concluida"] is False

    PessoaFactory(tenant=tenant)

    depois = api_autenticada.get(reverse("onboarding")).data
    assert missao(depois, "cadastrar_pessoa")["concluida"] is True
    assert depois["pontos"] == 10


def test_publicar_imovel_so_conta_quando_esta_no_ar(api_autenticada, imovel_publicavel):
    antes = api_autenticada.get(reverse("onboarding")).data
    assert missao(antes, "captar_imovel")["concluida"] is True
    assert missao(antes, "publicar_imovel")["concluida"] is False

    publicar(imovel_publicavel)

    depois = api_autenticada.get(reverse("onboarding")).data
    assert missao(depois, "publicar_imovel")["concluida"] is True


def test_proxima_missao_avanca_conforme_o_progresso(api_autenticada, tenant, proprietario):
    ImovelFactory(tenant=tenant, proprietario=proprietario)

    dados = api_autenticada.get(reverse("onboarding")).data

    # Pessoa e imóvel já existem; a próxima pendência é publicar.
    assert dados["proxima_missao"] == "publicar_imovel"


def test_nivel_sobe_com_os_pontos(api_autenticada, tenant, proprietario, corretor):
    ImovelFactory(tenant=tenant, proprietario=proprietario, com_fotos=5)
    LeadFactory(tenant=tenant, corretor=corretor)

    dados = api_autenticada.get(reverse("onboarding")).data

    assert dados["pontos"] >= 25
    assert dados["nivel"] in {"Aprendiz", "Operando"}


def test_missoes_financeiras_nao_aparecem_para_corretor(api, corretor):
    api.force_authenticate(user=corretor)

    dados = api.get(reverse("onboarding")).data
    chaves = {m["chave"] for m in dados["missoes"]}

    assert "dar_baixa" not in chaves
    assert "liquidar_repasse" not in chaves
    assert "captar_imovel" in chaves


def test_missoes_financeiras_aparecem_para_o_financeiro(api, financeiro):
    api.force_authenticate(user=financeiro)

    chaves = {m["chave"] for m in api.get(reverse("onboarding")).data["missoes"]}

    assert "dar_baixa" in chaves


def test_trilhas_resumem_o_progresso(api_autenticada, tenant):
    PessoaFactory(tenant=tenant)

    trilhas = {
        t["chave"]: t for t in api_autenticada.get(reverse("onboarding")).data["trilhas"]
    }

    assert trilhas["carteira"]["concluidas"] == 1
    assert trilhas["carteira"]["total"] == 3
    assert trilhas["comercial"]["concluidas"] == 0


def test_tour_concluido_fica_registrado(api_autenticada, admin_imobiliaria):
    resposta = api_autenticada.post(
        reverse("onboarding-concluir-tour", args=["primeiros-passos"])
    )

    assert "primeiros-passos" in resposta.data["tours_concluidos"]
    assert ProgressoOnboarding.objects.get(usuario=admin_imobiliaria).tours_concluidos == [
        "primeiros-passos"
    ]


def test_concluir_o_mesmo_tour_duas_vezes_nao_duplica(api_autenticada):
    url = reverse("onboarding-concluir-tour", args=["primeiros-passos"])
    api_autenticada.post(url)
    resposta = api_autenticada.post(url)

    assert resposta.data["tours_concluidos"] == ["primeiros-passos"]


def test_dispensar_e_voltar_atras(api_autenticada):
    dispensado = api_autenticada.post(
        reverse("onboarding-dispensar"), {"dispensado": True}, format="json"
    )
    assert dispensado.data["dispensado"] is True

    retomado = api_autenticada.post(
        reverse("onboarding-dispensar"), {"dispensado": False}, format="json"
    )
    assert retomado.data["dispensado"] is False


def test_reiniciar_limpa_o_guia_sem_tocar_na_operacao(api_autenticada, tenant):
    PessoaFactory(tenant=tenant)
    api_autenticada.post(reverse("onboarding-concluir-tour", args=["primeiros-passos"]))
    api_autenticada.post(
        reverse("onboarding-dispensar"), {"dispensado": True}, format="json"
    )

    resposta = api_autenticada.post(reverse("onboarding-reiniciar"))

    assert resposta.data["tours_concluidos"] == []
    assert resposta.data["dispensado"] is False
    # A missão continua concluída: o dado real não foi tocado.
    assert missao(resposta.data, "cadastrar_pessoa")["concluida"] is True


def test_onboarding_exige_autenticacao(api):
    assert api.get(reverse("onboarding")).status_code == 401


def test_progresso_de_um_usuario_nao_vaza_para_outro(api, admin_imobiliaria, corretor):
    api.force_authenticate(user=admin_imobiliaria)
    api.post(reverse("onboarding-concluir-tour", args=["primeiros-passos"]))

    api.force_authenticate(user=corretor)
    dados = api.get(reverse("onboarding")).data

    assert dados["tours_concluidos"] == []


def test_conclusao_e_carimbada_quando_tudo_termina(api, financeiro, tenant, corretor):
    """Com todas as missões do papel cumpridas, o guia marca a data de conclusão."""

    from datetime import timedelta

    from django.utils import timezone

    from apps.contratos.services import ativar_contrato
    from apps.contratos.tests.factories import ContratoFactory, montar_partes
    from apps.crm.services import agendar_visita, criar_proposta, marcar_primeiro_contato
    from apps.locacao.services import baixar_cobranca, liquidar_repasse
    from apps.pessoas.tests.factories import PessoaFactory
    from apps.vistorias.services import criar_vistoria, finalizar_vistoria

    proprietario = PessoaFactory(tenant=tenant)
    imovel = publicar(
        ImovelFactory(
            tenant=tenant, proprietario=proprietario, captador=corretor, com_fotos=5
        )
    )
    lead = LeadFactory(tenant=tenant, corretor=corretor, imovel_interesse=imovel)
    marcar_primeiro_contato(lead)
    agendar_visita(lead, imovel, timezone.now() + timedelta(days=1))
    criar_proposta(
        lead,
        imovel,
        {
            "valor_ofertado": "2000.00",
            "condicoes_pagamento": "à vista",
            "validade": timezone.localdate() + timedelta(days=5),
        },
    )

    contrato = ContratoFactory(tenant=tenant, imovel=imovel)
    montar_partes(contrato, proprietario, PessoaFactory(tenant=tenant))
    ativar_contrato(contrato)

    cobranca = contrato.cobrancas.order_by("competencia").first()
    baixar_cobranca(cobranca, cobranca.valor_total)
    liquidar_repasse(cobranca.repasse)
    finalizar_vistoria(criar_vistoria(contrato, "ENTRADA"))

    api.force_authenticate(user=financeiro)
    dados = api.get(reverse("onboarding")).data

    assert dados["concluido"] is True
    assert dados["percentual"] == 100
    assert dados["nivel"] == "Imobiliária no controle"
    assert ProgressoOnboarding.objects.get(usuario=financeiro).concluido_em is not None


def test_operador_da_plataforma_nao_tem_guia(api, django_user_model):
    """Superadmin não pertence a nenhuma imobiliária: o guia não se aplica."""

    operador = django_user_model.objects.create_user(
        email="operador@plataforma.test",
        password="senha-de-teste-123",
        nome_completo="Operador",
        papel="SUPERADMIN",
        tenant=None,
    )
    api.force_authenticate(operador)

    resposta = api.get(reverse("onboarding"))

    assert resposta.status_code == 403
    assert not ProgressoOnboarding.objects.filter(usuario=operador).exists()
