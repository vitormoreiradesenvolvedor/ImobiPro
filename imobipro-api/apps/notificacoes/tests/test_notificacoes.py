import pytest
from django.urls import reverse

from apps.notificacoes.models import Notificacao, TipoNotificacao
from apps.notificacoes.services import notificar_equipe, notificar_usuario

pytestmark = pytest.mark.django_db


def test_notificacao_e_gravada_para_o_usuario(corretor):
    notificacao = notificar_usuario(
        corretor, TipoNotificacao.LEAD_NOVO, "Novo lead", "Veio do site"
    )

    assert notificacao.tenant_id == corretor.tenant_id
    assert notificacao.lida is False


def test_notificar_equipe_atinge_todos_os_papeis_pedidos(
    tenant, admin_imobiliaria, gerente, corretor
):
    from apps.accounts.models import Papel

    criadas = notificar_equipe(
        tenant, [Papel.ADMIN, Papel.GERENTE], TipoNotificacao.PROPOSTA_RECEBIDA, "Proposta"
    )

    destinatarios = {n.usuario_id for n in criadas}
    assert destinatarios == {admin_imobiliaria.id, gerente.id}


def test_usuario_so_ve_as_proprias_notificacoes(api, corretor, gerente):
    notificar_usuario(corretor, TipoNotificacao.LEAD_NOVO, "Minha")
    notificar_usuario(gerente, TipoNotificacao.LEAD_NOVO, "Do colega")
    api.force_authenticate(user=corretor)

    resposta = api.get(reverse("notificacao-list"))

    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["titulo"] == "Minha"


def test_contador_de_nao_lidas(api, corretor):
    notificar_usuario(corretor, TipoNotificacao.LEAD_NOVO, "A")
    notificar_usuario(corretor, TipoNotificacao.LEAD_NOVO, "B")
    api.force_authenticate(user=corretor)

    assert api.get(reverse("notificacao-nao-lidas")).data["nao_lidas"] == 2


def test_marcar_uma_como_lida(api, corretor):
    notificacao = notificar_usuario(corretor, TipoNotificacao.LEAD_NOVO, "A")
    api.force_authenticate(user=corretor)

    resposta = api.post(reverse("notificacao-marcar-lida", args=[notificacao.pk]))

    assert resposta.data["lida"] is True
    notificacao.refresh_from_db()
    assert notificacao.lida_em is not None


def test_marcar_todas_como_lidas(api, corretor):
    notificar_usuario(corretor, TipoNotificacao.LEAD_NOVO, "A")
    notificar_usuario(corretor, TipoNotificacao.SLA_ESTOURANDO, "B")
    api.force_authenticate(user=corretor)

    api.post(reverse("notificacao-marcar-todas-lidas"))

    assert Notificacao.objects.filter(usuario=corretor, lida=False).count() == 0


def test_notificacao_de_outro_tenant_nao_aparece(api, corretor, outro_tenant):
    from apps.accounts.tests.factories import UsuarioFactory

    forasteiro = UsuarioFactory(tenant=outro_tenant)
    notificar_usuario(forasteiro, TipoNotificacao.LEAD_NOVO, "Alheia")
    api.force_authenticate(user=corretor)

    assert api.get(reverse("notificacao-list")).data["count"] == 0
