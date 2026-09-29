from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Papel
from apps.accounts.tests.factories import UsuarioFactory
from apps.crm.models import EstagioLead, Lead, TipoInteracao
from apps.crm.services import criar_lead, marcar_primeiro_contato, proximo_corretor
from apps.crm.tests.factories import LeadFactory
from apps.notificacoes.models import Notificacao

pytestmark = pytest.mark.django_db


PAYLOAD = {
    "nome": "Rafael Menezes",
    "email": "rafael@cliente.test",
    "telefone": "35991110000",
    "origem": "TELEFONE",
    "valor_estimado": "420000.00",
}


# ------------------------------------------------------------- distribuição


def test_lead_novo_e_distribuido_para_corretor(api_autenticada, tenant, corretor):
    resposta = api_autenticada.post(reverse("lead-list"), PAYLOAD, format="json")

    assert resposta.status_code == 201
    assert Lead.objects.get(pk=resposta.data["id"]).corretor_id == corretor.id


def test_distribuicao_escolhe_quem_tem_menos_lead_aberto(tenant, corretor):
    ocupado = corretor
    livre = UsuarioFactory(tenant=tenant, papel=Papel.CORRETOR)
    LeadFactory.create_batch(3, tenant=tenant, corretor=ocupado)

    assert proximo_corretor(tenant).pk == livre.pk


def test_captador_do_imovel_tem_preferencia(tenant, corretor, imovel):
    UsuarioFactory(tenant=tenant, papel=Papel.CORRETOR)  # ocioso, mas não captou

    assert proximo_corretor(tenant, imovel).pk == corretor.pk


def test_lead_atribuido_gera_notificacao_para_o_corretor(tenant, corretor):
    criar_lead({"nome": "X", "origem": "SITE"}, tenant)

    notificacao = Notificacao.objects.get(usuario=corretor)
    assert notificacao.tipo == "LEAD_NOVO"


def test_sem_corretor_ativo_a_gestao_e_avisada(tenant, admin_imobiliaria):
    criar_lead({"nome": "Sem dono", "origem": "SITE"}, tenant)

    assert Notificacao.objects.filter(usuario=admin_imobiliaria).exists()


def test_gestao_redistribui_lead(api_autenticada, tenant, corretor):
    lead = LeadFactory(tenant=tenant, corretor=corretor)
    outro = UsuarioFactory(tenant=tenant, papel=Papel.CORRETOR)

    resposta = api_autenticada.post(
        reverse("lead-atribuir", args=[lead.pk]),
        {"corretor_id": str(outro.pk)},
        format="json",
    )

    assert resposta.status_code == 200
    lead.refresh_from_db()
    assert lead.corretor_id == outro.pk


def test_corretor_nao_redistribui_lead(api, tenant, corretor):
    lead = LeadFactory(tenant=tenant, corretor=corretor)
    api.force_authenticate(user=corretor)

    resposta = api.post(
        reverse("lead-atribuir", args=[lead.pk]),
        {"corretor_id": str(corretor.pk)},
        format="json",
    )

    assert resposta.status_code == 400


# ---------------------------------------------------------------------- SLA


def test_interacao_humana_fecha_o_cronometro_do_sla(api, tenant, corretor):
    lead = LeadFactory(tenant=tenant, corretor=corretor)
    api.force_authenticate(user=corretor)

    api.post(
        reverse("lead-interacoes", args=[lead.pk]),
        {"tipo": "LIGACAO", "descricao": "Cliente atendeu, quer visitar sábado."},
        format="json",
    )

    lead.refresh_from_db()
    assert lead.primeiro_contato_em is not None
    assert lead.sla_cumprido is True
    assert lead.estagio == EstagioLead.EM_CONTATO


def test_contato_fora_do_prazo_marca_sla_descumprido(tenant, corretor):
    lead = LeadFactory(
        tenant=tenant,
        corretor=corretor,
        atribuido_em=timezone.now() - timedelta(minutes=40),
    )

    marcar_primeiro_contato(lead)

    assert lead.sla_cumprido is False


def test_lead_com_sla_estourado_volta_para_a_fila(tenant, corretor):
    from apps.crm.tasks import verificar_sla_de_atendimento

    outro = UsuarioFactory(tenant=tenant, papel=Papel.CORRETOR)
    lead = LeadFactory(
        tenant=tenant,
        corretor=corretor,
        atribuido_em=timezone.now() - timedelta(minutes=20),
    )

    assert verificar_sla_de_atendimento() == 1

    lead.refresh_from_db()
    assert lead.sla_cumprido is False
    assert lead.corretor_id == outro.pk  # quem deixou estourar não recebe de volta


def test_lead_ja_atendido_nao_volta_para_a_fila(tenant, corretor):
    from apps.crm.tasks import verificar_sla_de_atendimento

    LeadFactory(
        tenant=tenant,
        corretor=corretor,
        atribuido_em=timezone.now() - timedelta(minutes=30),
        primeiro_contato_em=timezone.now() - timedelta(minutes=25),
    )

    assert verificar_sla_de_atendimento() == 0


def test_aviso_antes_de_estourar_o_sla(tenant, corretor):
    from apps.crm.tasks import avisar_sla_proximo_do_limite

    LeadFactory(
        tenant=tenant,
        corretor=corretor,
        atribuido_em=timezone.now() - timedelta(minutes=12),
    )

    assert avisar_sla_proximo_do_limite() == 1
    assert Notificacao.objects.filter(tipo="SLA_ESTOURANDO").exists()


def test_minutos_para_sla_fica_negativo_quando_estoura(tenant, corretor):
    lead = LeadFactory(
        tenant=tenant,
        corretor=corretor,
        atribuido_em=timezone.now() - timedelta(minutes=20),
    )

    assert lead.minutos_para_sla < 0
    assert lead.sla_estourado is True


# --------------------------------------------------------------- funil


def test_mover_lead_pelo_kanban(api_autenticada, tenant, corretor):
    lead = LeadFactory(tenant=tenant, corretor=corretor)

    resposta = api_autenticada.patch(
        reverse("lead-mover", args=[lead.pk]),
        {"estagio": "QUALIFICADO"},
        format="json",
    )

    assert resposta.status_code == 200
    assert resposta.data["estagio"] == "QUALIFICADO"


def test_perder_lead_exige_motivo(api_autenticada, tenant, corretor):
    lead = LeadFactory(tenant=tenant, corretor=corretor)

    resposta = api_autenticada.patch(
        reverse("lead-mover", args=[lead.pk]),
        {"estagio": "FECHADO_PERDIDO"},
        format="json",
    )

    assert resposta.status_code == 400
    assert "motivo" in str(resposta.data["campos"]["estagio"]).lower()


def test_perda_com_motivo_registra_fechamento(api_autenticada, tenant, corretor):
    lead = LeadFactory(tenant=tenant, corretor=corretor)

    resposta = api_autenticada.patch(
        reverse("lead-mover", args=[lead.pk]),
        {"estagio": "FECHADO_PERDIDO", "motivo_perda": "PRECO", "observacao": "achou caro"},
        format="json",
    )

    assert resposta.status_code == 200
    lead.refresh_from_db()
    assert lead.motivo_perda == "PRECO"
    assert lead.fechado_em is not None


def test_movimentacao_registra_interacao_de_sistema(api_autenticada, tenant, corretor):
    lead = LeadFactory(tenant=tenant, corretor=corretor)

    api_autenticada.patch(
        reverse("lead-mover", args=[lead.pk]), {"estagio": "QUALIFICADO"}, format="json"
    )

    assert lead.interacoes.filter(tipo=TipoInteracao.SISTEMA).count() >= 1


def test_funil_devolve_colunas_com_total_e_valor(api_autenticada, tenant, corretor):
    LeadFactory.create_batch(
        2,
        tenant=tenant,
        corretor=corretor,
        estagio=EstagioLead.NOVO,
        valor_estimado="100000.00",
    )
    LeadFactory(
        tenant=tenant,
        corretor=corretor,
        estagio=EstagioLead.PROPOSTA,
        valor_estimado="500000.00",
    )

    colunas = {c["estagio"]: c for c in api_autenticada.get(reverse("lead-funil")).data}

    assert colunas["NOVO"]["total"] == 2
    assert float(colunas["NOVO"]["valor_total"]) == 200000.0
    assert colunas["PROPOSTA"]["total"] == 1
    assert "FECHADO_GANHO" not in colunas  # fechados não entram no kanban


def test_estatisticas_calculam_conversao_e_sla(api_autenticada, tenant, corretor):
    LeadFactory(
        tenant=tenant,
        corretor=corretor,
        estagio=EstagioLead.FECHADO_GANHO,
        sla_cumprido=True,
    )
    LeadFactory(
        tenant=tenant,
        corretor=corretor,
        estagio=EstagioLead.FECHADO_PERDIDO,
        motivo_perda="PRECO",
        sla_cumprido=False,
    )
    LeadFactory(tenant=tenant, corretor=corretor, estagio=EstagioLead.NEGOCIACAO)

    dados = api_autenticada.get(reverse("lead-estatisticas")).data

    assert dados["total_geral"] == 3
    assert dados["ganhos"] == 1
    assert dados["taxa_conversao"] == 50.0
    assert dados["sla_cumprido_percentual"] == 50.0
    # O relatório mostra o motivo por extenso, como estágio e origem já faziam.
    assert dados["por_motivo_perda"]["Preço acima do esperado"] == 1


# ------------------------------------------------------------- escopo


def test_corretor_so_ve_a_propria_carteira(api, tenant, corretor):
    LeadFactory(tenant=tenant, corretor=corretor, nome="Meu")
    LeadFactory(
        tenant=tenant,
        corretor=UsuarioFactory(tenant=tenant, papel=Papel.CORRETOR),
        nome="Do colega",
    )
    api.force_authenticate(user=corretor)

    resposta = api.get(reverse("lead-list"))

    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["nome"] == "Meu"


def test_gerente_ve_a_equipe_inteira(api, tenant, gerente, corretor):
    LeadFactory(tenant=tenant, corretor=corretor)
    LeadFactory(tenant=tenant, corretor=None)
    api.force_authenticate(user=gerente)

    assert api.get(reverse("lead-list")).data["count"] == 2


def test_lead_de_outro_tenant_nao_aparece(api_autenticada, outro_tenant):
    LeadFactory(tenant=outro_tenant)

    assert api_autenticada.get(reverse("lead-list")).data["count"] == 0
