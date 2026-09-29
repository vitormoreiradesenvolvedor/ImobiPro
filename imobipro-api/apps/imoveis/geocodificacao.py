"""Coordenadas a partir do endereço, pelo Nominatim (OpenStreetMap).

Serviço aberto, sem chave e sem custo, que é o mesmo mapa usado na vitrine.
Em troca, ele pede duas coisas na política de uso: identificar a aplicação no
User-Agent e não martelar o serviço. Por isso todo resultado fica em cache por
30 dias e a busca só acontece quando o imóvel ainda não tem coordenada.

Sem latitude e longitude o imóvel não entra no mapa nem pode ser publicado, e
digitar coordenada na mão é o tipo de tarefa que ninguém faz.
"""

import hashlib
import json
import logging
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
IDENTIFICACAO = f"ImobiPro/1.0 (gestao imobiliaria; {settings.CONTATO_GEOCODIFICACAO})"
TTL_CACHE = 60 * 60 * 24 * 30
TIMEOUT = 6


class EnderecoNaoLocalizado(Exception):
    """Endereço que o mapa não reconheceu; o usuário informa na mão."""


def _consultar(**parametros) -> list:
    """Busca estruturada do Nominatim.

    A busca livre (`q=`) erra feio com endereço brasileiro: "Praça Dr. Augusto
    Silva, Centro, Lavras, MG" não devolve nada, enquanto os campos separados
    (rua, cidade, estado) acham na primeira tentativa.
    """

    consulta = urlencode(
        {**parametros, "format": "jsonv2", "limit": 1, "countrycodes": "br"}
    )
    # A URL é montada aqui a partir de constante: não vem de entrada do usuário.
    requisicao = Request(  # noqa: S310
        f"{URL_NOMINATIM}?{consulta}",
        headers={"User-Agent": IDENTIFICACAO, "Accept-Language": "pt-BR"},
    )
    with urlopen(requisicao, timeout=TIMEOUT) as resposta:  # noqa: S310
        return json.loads(resposta.read().decode("utf-8"))


def _tentativas(endereco) -> list:
    """Do mais específico ao mais genérico, sem nunca inventar localização.

    Loteamento novo e endereço abreviado quase sempre falham com o número. Um
    pino na rua certa serve para quem procura imóvel; um pino na cidade errada,
    não. Por isso a última tentativa ainda amarra bairro e cidade.
    """

    rua = endereco.logradouro or ""
    cidade = endereco.cidade or ""
    estado = endereco.uf or ""
    bairro = endereco.bairro or ""

    tentativas = []
    if rua and cidade:
        if endereco.numero:
            tentativas.append(
                {"street": f"{rua}, {endereco.numero}", "city": cidade, "state": estado}
            )
        tentativas.append({"street": rua, "city": cidade, "state": estado})
    if bairro and cidade:
        tentativas.append({"q": f"{bairro}, {cidade}, {estado}"})
    return tentativas


def _chave_de_cache(endereco) -> str:
    """Endereço tem espaço e acento; a chave precisa ser curta e previsível."""

    bruto = "|".join(
        [
            endereco.logradouro or "",
            endereco.numero or "",
            endereco.bairro or "",
            endereco.cidade or "",
            endereco.uf or "",
        ]
    ).lower()
    return "geo:" + hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:32]


def coordenadas_do_endereco(endereco) -> tuple:
    """Devolve (latitude, longitude) como Decimal. Levanta EnderecoNaoLocalizado."""

    tentativas = _tentativas(endereco)
    if not tentativas:
        raise EnderecoNaoLocalizado("Informe ao menos rua e cidade.")

    chave = _chave_de_cache(endereco)
    if (guardado := cache.get(chave)) is not None:
        if guardado == "sem_resultado":
            raise EnderecoNaoLocalizado("Endereço não encontrado no mapa.")
        return Decimal(guardado[0]), Decimal(guardado[1])

    encontrado = None
    for parametros in tentativas:
        try:
            resultados = _consultar(**parametros)
        except (URLError, TimeoutError, json.JSONDecodeError) as falha:
            logger.warning("Falha ao geocodificar %s: %s", parametros, falha)
            raise EnderecoNaoLocalizado(
                "Serviço de mapas indisponível. Informe latitude e longitude."
            ) from falha
        if resultados:
            encontrado = resultados[0]
            break

    if not encontrado:
        cache.set(chave, "sem_resultado", TTL_CACHE)
        raise EnderecoNaoLocalizado(
            "Endereço não encontrado no mapa. Confira a rua, o bairro e a cidade."
        )

    try:
        latitude = Decimal(str(encontrado["lat"]))
        longitude = Decimal(str(encontrado["lon"]))
    except (KeyError, InvalidOperation) as falha:
        raise EnderecoNaoLocalizado("Resposta do mapa em formato inesperado.") from falha

    cache.set(chave, [str(latitude), str(longitude)], TTL_CACHE)
    return latitude, longitude


def geocodificar_imovel(imovel):
    """Preenche as coordenadas do imóvel quando ainda não existirem.

    Não sobrescreve coordenada informada por alguém: quem posicionou o pino no
    mapa sabe mais sobre o imóvel do que a busca por texto.
    """

    endereco = imovel.endereco
    if endereco.latitude and endereco.longitude:
        return endereco.latitude, endereco.longitude

    latitude, longitude = coordenadas_do_endereco(endereco)
    endereco.latitude = latitude
    endereco.longitude = longitude
    endereco.save(update_fields=["latitude", "longitude"])
    return latitude, longitude
