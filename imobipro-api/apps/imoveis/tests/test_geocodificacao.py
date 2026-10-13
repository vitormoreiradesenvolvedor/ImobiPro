"""Coordenadas pelo Nominatim: sem elas o imóvel não entra no mapa.

A rede não é tocada aqui. O que se testa é a estratégia: tentar do endereço
completo até o bairro, guardar o resultado e nunca sobrescrever coordenada que
alguém já posicionou.
"""

from decimal import Decimal

import pytest

from apps.imoveis import geocodificacao
from apps.imoveis.geocodificacao import (
    EnderecoNaoLocalizado,
    coordenadas_do_endereco,
    geocodificar_imovel,
)
from apps.pessoas.models import Endereco

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpo():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


def endereco(**campos):
    padrao = {
        "logradouro": "Avenida Central",
        "numero": "291",
        "bairro": "Centro",
        "cidade": "Lavras",
        "uf": "MG",
        "cep": "37200000",
    }
    return Endereco(**{**padrao, **campos})


def responder(monkeypatch, respostas):
    """Cada chamada devolve a próxima resposta da fila e registra a consulta."""

    consultas = []

    def falso(**parametros):
        consultas.append(parametros)
        return respostas.pop(0) if respostas else []

    monkeypatch.setattr(geocodificacao, "_consultar", falso)
    return consultas


def test_usa_o_endereco_completo_quando_ele_e_reconhecido(monkeypatch):
    consultas = responder(monkeypatch, [[{"lat": "-21.24", "lon": "-44.99"}]])

    assert coordenadas_do_endereco(endereco()) == (Decimal("-21.24"), Decimal("-44.99"))
    assert len(consultas) == 1
    assert consultas[0]["street"] == "Avenida Central, 291"


def test_tenta_sem_o_numero_antes_de_desistir(monkeypatch):
    """Loteamento novo quase nunca tem o número no mapa."""

    consultas = responder(monkeypatch, [[], [{"lat": "-21.22", "lon": "-44.97"}]])

    latitude, _ = coordenadas_do_endereco(endereco())

    assert latitude == Decimal("-21.22")
    assert consultas[1]["street"] == "Avenida Central"


def test_ultima_alternativa_amarra_bairro_e_cidade(monkeypatch):
    consultas = responder(monkeypatch, [[], [], [{"lat": "-21.20", "lon": "-44.90"}]])

    coordenadas_do_endereco(endereco())

    assert consultas[2]["q"] == "Centro, Lavras, MG"


def test_endereco_desconhecido_avisa_em_vez_de_chutar(monkeypatch):
    responder(monkeypatch, [[], [], []])

    alvo = endereco()

    with pytest.raises(EnderecoNaoLocalizado, match="não encontrado"):
        coordenadas_do_endereco(alvo)


def test_resultado_fica_em_cache_para_nao_martelar_o_servico(monkeypatch):
    consultas = responder(monkeypatch, [[{"lat": "-21.24", "lon": "-44.99"}]])

    coordenadas_do_endereco(endereco())
    coordenadas_do_endereco(endereco())

    assert len(consultas) == 1


def test_endereco_sem_rua_nem_cidade_nao_vai_para_a_rede(monkeypatch):
    consultas = responder(monkeypatch, [])

    vazio = Endereco(logradouro="", cidade="")

    with pytest.raises(EnderecoNaoLocalizado, match="rua e cidade"):
        coordenadas_do_endereco(vazio)

    assert consultas == []


def test_coordenada_informada_por_alguem_nao_e_sobrescrita(monkeypatch, imovel):
    """Quem arrastou o pino no mapa sabe mais que a busca por texto."""

    consultas = responder(monkeypatch, [[{"lat": "-1.00", "lon": "-2.00"}]])
    imovel.endereco.latitude = Decimal("-21.111111")
    imovel.endereco.longitude = Decimal("-44.222222")
    imovel.endereco.save()

    latitude, longitude = geocodificar_imovel(imovel)

    assert (latitude, longitude) == (Decimal("-21.111111"), Decimal("-44.222222"))
    assert consultas == []


def test_geocodificar_grava_no_endereco_do_imovel(monkeypatch, imovel):
    responder(monkeypatch, [[{"lat": "-21.245", "lon": "-44.997"}]])
    imovel.endereco.latitude = None
    imovel.endereco.longitude = None
    imovel.endereco.save()

    geocodificar_imovel(imovel)
    imovel.endereco.refresh_from_db()

    assert imovel.endereco.latitude == Decimal("-21.245")
    assert imovel.endereco.longitude == Decimal("-44.997")
