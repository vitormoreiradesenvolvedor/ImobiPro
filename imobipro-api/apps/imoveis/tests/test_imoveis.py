import pytest
from django.urls import reverse

from apps.imoveis.models import Imovel, SituacaoImovel
from apps.imoveis.services import RegraDeNegocio, criar_imovel, mudar_situacao, publicar
from apps.imoveis.tests.factories import CaracteristicaFactory, ImovelFactory
from apps.pessoas.tests.factories import PessoaFactory

pytestmark = pytest.mark.django_db


def payload_imovel(proprietario):
    return {
        "titulo": "Apartamento 2 quartos no Centro",
        "descricao": "Reformado, com armários e vaga coberta.",
        "tipo": "APARTAMENTO",
        "finalidade": "LOCACAO",
        "proprietario": str(proprietario.pk),
        "quartos": 2,
        "banheiros": 1,
        "vagas": 1,
        "valor_locacao": "2500.00",
        "matricula": "98765",
        "endereco": {
            "logradouro": "Rua Minas Gerais",
            "numero": "300",
            "bairro": "Centro",
            "cidade": "Lavras",
            "uf": "MG",
            "latitude": "-21.245",
            "longitude": "-44.999",
        },
    }


# --------------------------------------------------------------- cadastro


def test_codigo_e_sequencial_por_imobiliaria(api_autenticada, proprietario, tenant):
    primeiro = api_autenticada.post(
        reverse("imovel-list"), payload_imovel(proprietario), format="json"
    )
    segundo = api_autenticada.post(
        reverse("imovel-list"), payload_imovel(proprietario), format="json"
    )

    assert primeiro.data["codigo"] == "REF-000001"
    assert segundo.data["codigo"] == "REF-000002"


def test_codigo_reinicia_em_cada_imobiliaria(tenant, outro_tenant, proprietario):
    outro_proprietario = PessoaFactory(tenant=outro_tenant)

    a = criar_imovel(
        {
            "titulo": "A",
            "tipo": "CASA",
            "finalidade": "VENDA",
            "proprietario": proprietario,
            "endereco": proprietario.endereco,
        },
        tenant,
    )
    b = criar_imovel(
        {
            "titulo": "B",
            "tipo": "CASA",
            "finalidade": "VENDA",
            "proprietario": outro_proprietario,
            "endereco": outro_proprietario.endereco,
        },
        outro_tenant,
    )

    assert a.codigo == b.codigo == "REF-000001"


def test_captador_padrao_e_quem_cadastrou(api, corretor, proprietario):
    api.force_authenticate(user=corretor)

    resposta = api.post(reverse("imovel-list"), payload_imovel(proprietario), format="json")

    assert Imovel.objects.get(pk=resposta.data["id"]).captador_id == corretor.id


def test_imovel_nasce_em_captacao(api_autenticada, proprietario):
    resposta = api_autenticada.post(
        reverse("imovel-list"), payload_imovel(proprietario), format="json"
    )

    assert resposta.data["situacao"] == SituacaoImovel.EM_CAPTACAO
    assert resposta.data["publicado_site"] is False


def test_proprietario_de_outro_tenant_e_recusado(api_autenticada, outro_tenant):
    intruso = PessoaFactory(tenant=outro_tenant)

    resposta = api_autenticada.post(
        reverse("imovel-list"), payload_imovel(intruso), format="json"
    )

    assert resposta.status_code == 400


def test_finalidade_venda_nao_aceita_valor_de_locacao(api_autenticada, proprietario):
    payload = {
        **payload_imovel(proprietario),
        "finalidade": "VENDA",
        "valor_venda": "450000.00",
    }

    resposta = api_autenticada.post(reverse("imovel-list"), payload, format="json")

    assert resposta.status_code == 400
    assert "valor_locacao" in resposta.data["campos"]


# ------------------------------------------------------------- publicação


def test_publicacao_lista_todas_as_pendencias(api_autenticada, imovel):
    resposta = api_autenticada.post(reverse("imovel-publicar", args=[imovel.pk]))

    assert resposta.status_code == 400
    mensagem = str(resposta.data["campos"]["publicacao"])
    assert "5 fotos" in mensagem


def test_publica_quando_cumpre_todas_as_regras(api_autenticada, imovel_publicavel):
    resposta = api_autenticada.post(reverse("imovel-publicar", args=[imovel_publicavel.pk]))

    assert resposta.status_code == 200
    assert resposta.data["publicado_site"] is True
    # Publicar tira o imóvel da captação e o coloca como disponível.
    assert resposta.data["situacao"] == SituacaoImovel.DISPONIVEL


def test_locacao_sem_matricula_nao_publica(imovel_publicavel):
    imovel_publicavel.matricula = ""
    imovel_publicavel.save(update_fields=["matricula"])

    with pytest.raises(RegraDeNegocio, match="Matrícula"):
        publicar(imovel_publicavel)


def test_endereco_sem_coordenada_nao_publica(imovel_publicavel):
    imovel_publicavel.endereco.latitude = None
    imovel_publicavel.endereco.save()

    with pytest.raises(RegraDeNegocio, match="latitude"):
        publicar(imovel_publicavel)


def test_despublicar_registra_historico(api_autenticada, imovel_publicavel):
    publicar(imovel_publicavel)

    resposta = api_autenticada.post(
        reverse("imovel-despublicar", args=[imovel_publicavel.pk]),
        {"motivo": "proprietário desistiu"},
        format="json",
    )

    assert resposta.data["publicado_site"] is False
    assert imovel_publicavel.historico.filter(tipo="DESPUBLICACAO").exists()


# --------------------------------------------------- máquina de estados


def test_transicao_valida_muda_situacao(api_autenticada, imovel_publicavel):
    publicar(imovel_publicavel)

    resposta = api_autenticada.patch(
        reverse("imovel-situacao", args=[imovel_publicavel.pk]),
        {"situacao": "RESERVADO"},
        format="json",
    )

    assert resposta.data["situacao"] == "RESERVADO"


def test_transicao_invalida_e_recusada(api_autenticada, imovel):
    # EM_CAPTACAO não pode saltar direto para VENDIDO.
    resposta = api_autenticada.patch(
        reverse("imovel-situacao", args=[imovel.pk]),
        {"situacao": "VENDIDO"},
        format="json",
    )

    assert resposta.status_code == 400
    assert "Não é possível mudar" in str(resposta.data["campos"]["situacao"])


def test_imovel_vendido_sai_do_ar(imovel_publicavel):
    publicar(imovel_publicavel)
    mudar_situacao(imovel_publicavel, SituacaoImovel.VENDIDO)

    imovel_publicavel.refresh_from_db()
    assert imovel_publicavel.publicado_site is False


def test_mudanca_de_situacao_gera_historico(imovel_publicavel):
    publicar(imovel_publicavel)
    mudar_situacao(imovel_publicavel, SituacaoImovel.RESERVADO, motivo="proposta aceita")

    evento = imovel_publicavel.historico.filter(tipo="SITUACAO").first()
    assert "proposta aceita" in evento.descricao


# ------------------------------------------------------------------ fotos


def test_upload_de_fotos_define_capa_e_ordem(api_autenticada, imovel):
    from apps.imoveis.tests.factories import imagem_de_teste

    resposta = api_autenticada.post(
        reverse("imovel-enviar-fotos", args=[imovel.pk]),
        {"arquivo": [imagem_de_teste("a.png"), imagem_de_teste("b.png")]},
        format="multipart",
    )

    assert resposta.status_code == 201
    assert [f["ordem"] for f in resposta.data] == [0, 1]
    assert resposta.data[0]["capa"] is True


def test_reordenar_fotos_troca_a_capa(api_autenticada, imovel_publicavel):
    fotos = list(imovel_publicavel.fotos.all())
    nova_ordem = [str(fotos[2].pk), str(fotos[0].pk), str(fotos[1].pk)] + [
        str(f.pk) for f in fotos[3:]
    ]

    resposta = api_autenticada.patch(
        reverse("imovel-reordenar-fotos", args=[imovel_publicavel.pk]),
        {"ordem": nova_ordem},
        format="json",
    )

    assert resposta.status_code == 200
    fotos[2].refresh_from_db()
    assert fotos[2].capa is True


def test_reordenar_com_foto_de_outro_imovel_falha(
    api_autenticada, imovel_publicavel, tenant, proprietario
):
    outro = ImovelFactory(tenant=tenant, proprietario=proprietario, com_fotos=1)
    intrusa = outro.fotos.first()

    resposta = api_autenticada.patch(
        reverse("imovel-reordenar-fotos", args=[imovel_publicavel.pk]),
        {"ordem": [str(intrusa.pk)]},
        format="json",
    )

    assert resposta.status_code == 400


def test_remover_capa_promove_a_proxima_foto(api_autenticada, imovel_publicavel):
    capa = imovel_publicavel.fotos.get(capa=True)
    segunda = imovel_publicavel.fotos.exclude(pk=capa.pk).first()

    resposta = api_autenticada.delete(
        reverse("imovel-remover-foto", args=[imovel_publicavel.pk, capa.pk])
    )

    assert resposta.status_code == 204
    segunda.refresh_from_db()
    assert segunda.capa is True


# ---------------------------------------------------------------- filtros


def test_filtra_por_quartos_e_valor(api_autenticada, tenant, proprietario):
    ImovelFactory(tenant=tenant, proprietario=proprietario, quartos=1, valor_locacao="1200")
    ImovelFactory(tenant=tenant, proprietario=proprietario, quartos=3, valor_locacao="3000")

    resposta = api_autenticada.get(
        reverse("imovel-list"),
        {"finalidade": "LOCACAO", "quartos_min": 2, "valor_max": 3500},
    )

    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["quartos"] == 3


def test_filtra_por_caracteristicas_exigindo_todas(api_autenticada, tenant, proprietario):
    piscina = CaracteristicaFactory(slug="piscina", nome="Piscina")
    elevador = CaracteristicaFactory(slug="elevador", nome="Elevador")

    completo = ImovelFactory(tenant=tenant, proprietario=proprietario)
    completo.caracteristicas.set([piscina, elevador])
    parcial = ImovelFactory(tenant=tenant, proprietario=proprietario)
    parcial.caracteristicas.set([piscina])

    resposta = api_autenticada.get(
        reverse("imovel-list"), {"caracteristicas": "piscina,elevador"}
    )

    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["id"] == str(completo.pk)


def test_busca_textual_usa_indice_e_encontra_por_descricao(
    api_autenticada, tenant, proprietario
):
    from apps.imoveis.services import atualizar_indice_busca

    alvo = ImovelFactory(
        tenant=tenant,
        proprietario=proprietario,
        titulo="Cobertura duplex",
        descricao="Vista para a serra, com hidromassagem",
    )
    outro = ImovelFactory(
        tenant=tenant,
        proprietario=proprietario,
        titulo="Kitnet simples",
        descricao="Perto da universidade",
    )
    atualizar_indice_busca(alvo)
    atualizar_indice_busca(outro)

    resposta = api_autenticada.get(reverse("imovel-list"), {"search": "hidromassagem"})

    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["id"] == str(alvo.pk)


def test_filtra_por_raio_geografico(api_autenticada, tenant, proprietario):
    from apps.pessoas.tests.factories import EnderecoFactory

    perto = ImovelFactory(
        tenant=tenant,
        proprietario=proprietario,
        endereco=EnderecoFactory(latitude="-21.2450", longitude="-44.9990"),
    )
    ImovelFactory(  # São Paulo, ~330 km de Lavras
        tenant=tenant,
        proprietario=proprietario,
        endereco=EnderecoFactory(latitude="-23.5505", longitude="-46.6333"),
    )

    resposta = api_autenticada.get(
        reverse("imovel-list"), {"lat": "-21.245", "lng": "-44.999", "raio_km": "10"}
    )

    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["id"] == str(perto.pk)


def test_mapa_ignora_imovel_sem_coordenada(api_autenticada, tenant, proprietario):
    from apps.pessoas.tests.factories import EnderecoFactory

    ImovelFactory(tenant=tenant, proprietario=proprietario)
    ImovelFactory(
        tenant=tenant,
        proprietario=proprietario,
        endereco=EnderecoFactory(latitude=None, longitude=None),
    )

    resposta = api_autenticada.get(reverse("imovel-mapa"))

    assert len(resposta.data) == 1


# ------------------------------------------------------------ estatísticas


def test_estatisticas_agrupa_por_situacao_e_calcula_carteira(
    api_autenticada, tenant, proprietario
):
    ImovelFactory(
        tenant=tenant,
        proprietario=proprietario,
        finalidade="VENDA",
        situacao=SituacaoImovel.DISPONIVEL,
        valor_venda="400000",
        valor_locacao=None,
    )
    ImovelFactory(
        tenant=tenant,
        proprietario=proprietario,
        finalidade="VENDA",
        situacao=SituacaoImovel.DISPONIVEL,
        valor_venda="600000",
        valor_locacao=None,
    )
    ImovelFactory(tenant=tenant, proprietario=proprietario)  # em captação

    resposta = api_autenticada.get(reverse("imovel-estatisticas"))

    assert resposta.data["total_geral"] == 3
    assert resposta.data["por_situacao"]["Disponível"] == 2
    assert float(resposta.data["carteira_venda"]) == 1000000.0
    assert float(resposta.data["valor_medio_venda"]) == 500000.0


# ------------------------------------------------------ permissões e escopo


def test_corretor_nao_edita_imovel_de_outro_captador(api, corretor, tenant, proprietario):
    from apps.accounts.tests.factories import UsuarioFactory

    alheio = ImovelFactory(
        tenant=tenant, proprietario=proprietario, captador=UsuarioFactory(tenant=tenant)
    )
    api.force_authenticate(user=corretor)

    resposta = api.patch(
        reverse("imovel-detail", args=[alheio.pk]),
        {"titulo": "Sequestrado"},
        format="json",
    )

    assert resposta.status_code == 403


def test_financeiro_le_mas_nao_edita(api, financeiro, imovel):
    api.force_authenticate(user=financeiro)

    assert api.get(reverse("imovel-list")).status_code == 200
    assert (
        api.patch(
            reverse("imovel-detail", args=[imovel.pk]), {"titulo": "X"}, format="json"
        ).status_code
        == 403
    )


def test_imovel_de_outro_tenant_nao_aparece(api_autenticada, outro_tenant):
    ImovelFactory(tenant=outro_tenant, proprietario=PessoaFactory(tenant=outro_tenant))

    assert api_autenticada.get(reverse("imovel-list")).data["count"] == 0


def test_alteracao_de_valor_gera_auditoria_e_historico(api_autenticada, imovel):
    from apps.core.models import LogAuditoria

    api_autenticada.patch(
        reverse("imovel-detail", args=[imovel.pk]),
        {"valor_locacao": "2900.00"},
        format="json",
    )

    assert imovel.historico.filter(tipo="VALOR").exists()
    log = LogAuditoria.objects.filter(modelo="Imovel", objeto_id=str(imovel.pk)).first()
    assert log.alteracoes["valor_locacao"]["para"] == "2900.00"


def test_listagem_de_imoveis_nao_dispara_n_mais_um(api_autenticada, tenant, proprietario):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    ImovelFactory.create_batch(6, tenant=tenant, proprietario=proprietario, com_fotos=2)

    with CaptureQueriesContext(connection) as consultas:
        api_autenticada.get(reverse("imovel-list"))

    selects = [c for c in consultas.captured_queries if c["sql"].startswith("SELECT")]
    # COUNT + página + prefetch de fotos + prefetch de características.
    assert len(selects) <= 4, [c["sql"][:120] for c in selects]
