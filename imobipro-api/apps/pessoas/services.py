"""Consulta de CEP.

Usa a ViaCEP pela biblioteca padrão (sem dependência nova) e guarda o resultado
em cache por 30 dias: CEP não muda de bairro e a captação de imóvel consulta o
mesmo endereço várias vezes.
"""

import json
import logging
from urllib.error import URLError
from urllib.request import urlopen

from django.core.cache import cache

from apps.core.validators import somente_digitos

logger = logging.getLogger(__name__)

URL_VIACEP = "https://viacep.com.br/ws/{cep}/json/"
TTL_CACHE = 60 * 60 * 24 * 30
TIMEOUT = 4


class CepNaoEncontrado(Exception):
    pass


def _buscar_na_viacep(cep: str) -> dict:
    with urlopen(URL_VIACEP.format(cep=cep), timeout=TIMEOUT) as resposta:  # noqa: S310
        return json.loads(resposta.read().decode("utf-8"))


def consultar_cep(cep: str) -> dict:
    """Devolve o endereço no formato do nosso modelo. Levanta CepNaoEncontrado."""

    cep = somente_digitos(cep)
    if len(cep) != 8:
        raise CepNaoEncontrado("CEP deve ter 8 dígitos.")

    chave = f"cep:{cep}"
    if (guardado := cache.get(chave)) is not None:
        return guardado

    try:
        bruto = _buscar_na_viacep(cep)
    except (URLError, TimeoutError, json.JSONDecodeError) as falha:
        logger.warning("Falha ao consultar CEP %s: %s", cep, falha)
        raise CepNaoEncontrado(
            "Serviço de CEP indisponível. Preencha manualmente."
        ) from falha

    if bruto.get("erro"):
        raise CepNaoEncontrado("CEP não encontrado.")

    endereco = {
        "cep": cep,
        "logradouro": bruto.get("logradouro", ""),
        "bairro": bruto.get("bairro", ""),
        "cidade": bruto.get("localidade", ""),
        "uf": bruto.get("uf", ""),
    }
    cache.set(chave, endereco, TTL_CACHE)
    return endereco
