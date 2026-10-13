"""Vitrine pública: sem token, só o que a imobiliária realmente publicou."""

import pytest
from django.urls import reverse

from apps.imoveis.models import SituacaoImovel
from apps.imoveis.services import publicar
from apps.imoveis.tests.factories import ImovelFactory
from apps.pessoas.tests.factories import PessoaFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def publicado(tenant, proprietario, corretor):
    imovel = ImovelFactory(
        tenant=tenant, proprietario=proprietario, captador=corretor, com_fotos=5
    )
    return publicar(imovel)


def url_lista(tenant):
    return reverse("imovel-publico-list", kwargs={"subdominio": tenant.subdominio})


def test_vitrine_dispensa_autenticacao(api, tenant, publicado):
    resposta = api.get(url_lista(tenant))

    assert resposta.status_code == 200
    assert resposta.data["count"] == 1


def test_vitrine_esconde_imovel_nao_publicado(api, tenant, proprietario):
    ImovelFactory(tenant=tenant, proprietario=proprietario)

    assert api.get(url_lista(tenant)).data["count"] == 0


def test_vitrine_esconde_imovel_ja_vendido(api, tenant, publicado):
    publicado.situacao = SituacaoImovel.VENDIDO
    publicado.save(update_fields=["situacao"])

    assert api.get(url_lista(tenant)).data["count"] == 0


def test_vitrine_de_uma_imobiliaria_nao_mostra_a_de_outra(api, tenant, outro_tenant):
    alheio = ImovelFactory(
        tenant=outro_tenant, proprietario=PessoaFactory(tenant=outro_tenant), com_fotos=5
    )
    publicar(alheio)

    assert api.get(url_lista(tenant)).data["count"] == 0


def test_detalhe_publico_e_acessado_pelo_codigo(api, tenant, publicado):
    url = reverse(
        "imovel-publico-detail",
        kwargs={"subdominio": tenant.subdominio, "codigo": publicado.codigo},
    )

    resposta = api.get(url)

    assert resposta.status_code == 200
    assert resposta.data["codigo"] == publicado.codigo


def test_visita_ao_detalhe_publico_conta_visualizacao(api, tenant, publicado):
    url = reverse(
        "imovel-publico-detail",
        kwargs={"subdominio": tenant.subdominio, "codigo": publicado.codigo},
    )

    api.get(url)
    publicado.refresh_from_db()

    assert publicado.visualizacoes == 1


def test_vitrine_de_imobiliaria_inativa_fica_vazia(api, tenant, publicado):
    tenant.ativo = False
    tenant.save(update_fields=["ativo"])

    assert api.get(url_lista(tenant)).data["count"] == 0


# ------------------------------------------------------ catálogo categorizado


def url_categorias(tenant):
    return reverse("imovel-publico-categorias", kwargs={"subdominio": tenant.subdominio})


def test_catalogo_agrupa_o_que_esta_publicado(api, tenant, publicado):
    resposta = api.get(url_categorias(tenant))

    assert resposta.status_code == 200
    assert resposta.data["total"] == 1

    tipos = {linha["valor"]: linha["total"] for linha in resposta.data["por_tipo"]}
    assert tipos[publicado.tipo] == 1

    bairros = {linha["valor"] for linha in resposta.data["por_bairro"]}
    assert publicado.endereco.bairro in bairros


def test_catalogo_nao_mostra_prateleira_vazia(api, tenant, publicado):
    """Categoria sem imóvel só frustra quem está procurando."""

    resposta = api.get(url_categorias(tenant))

    for chave in ["por_tipo", "por_bairro", "por_finalidade", "por_faixa_de_aluguel"]:
        assert all(linha["total"] > 0 for linha in resposta.data[chave])


def test_catalogo_ignora_imovel_nao_publicado(api, tenant, proprietario, publicado):
    ImovelFactory(tenant=tenant, proprietario=proprietario)  # fica em captação

    resposta = api.get(url_categorias(tenant))

    assert resposta.data["total"] == 1


def test_catalogo_respeita_o_filtro_da_busca(api, tenant, publicado, proprietario):
    outro = ImovelFactory(
        tenant=tenant, proprietario=proprietario, com_fotos=5, tipo="TERRENO"
    )
    publicar(outro)

    resposta = api.get(url_categorias(tenant), {"tipo": "TERRENO"})

    assert resposta.data["total"] == 1
    assert resposta.data["por_tipo"][0]["valor"] == "TERRENO"


# --------------------------------------------------------- banner e destaque


def test_destaques_caem_para_os_mais_vistos_quando_nao_ha_banner(api, tenant, publicado):
    url = reverse("imovel-publico-destaques", kwargs={"subdominio": tenant.subdominio})

    resposta = api.get(url)

    assert resposta.status_code == 200
    assert len(resposta.data) == 1


def test_ficha_publica_traz_as_midias_do_anuncio(api, tenant, publicado):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.imoveis.models import MidiaImovel, TipoMidia

    MidiaImovel.objects.create(
        imovel=publicado,
        tipo=TipoMidia.VIDEO,
        arquivo=SimpleUploadedFile("tour.mp4", b"video", content_type="video/mp4"),
        titulo="Tour pelo apartamento",
        destaque=True,
    )

    url = reverse(
        "imovel-publico-detail",
        kwargs={"subdominio": tenant.subdominio, "codigo": publicado.codigo},
    )
    resposta = api.get(url)

    assert resposta.status_code == 200
    assert len(resposta.data["midias"]) == 1
    assert resposta.data["midias"][0]["tipo"] == "VIDEO"
    assert resposta.data["midias"][0]["titulo"] == "Tour pelo apartamento"
