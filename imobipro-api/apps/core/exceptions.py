"""Formato único de erro da API: {detail, code, campos}."""

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler


def _espera_legivel(segundos):
    """ "Disponível em 3305 segundos" não diz nada a quem está na tela."""

    if not segundos:
        return "Muitas tentativas. Tente de novo em instantes."

    minutos = int(segundos) // 60
    if minutos >= 60:
        horas = minutos // 60
        return f"Muitas tentativas. Tente de novo em {horas} hora(s)."
    if minutos >= 1:
        return f"Muitas tentativas. Tente de novo em {minutos} minuto(s)."
    return f"Muitas tentativas. Tente de novo em {int(segundos)} segundos."


def exception_handler_padrao(exc, context):
    resposta = exception_handler(exc, context)
    if resposta is None:
        return None

    if isinstance(exc, Throttled):
        resposta.data = {
            "detail": _espera_legivel(exc.wait),
            "code": "limite_de_requisicoes",
            "campos": {},
        }
        return resposta

    dados = resposta.data
    codigo = getattr(exc, "default_code", "erro")

    if isinstance(dados, dict) and "detail" in dados:
        resposta.data = {"detail": str(dados["detail"]), "code": codigo, "campos": {}}
    elif isinstance(dados, dict):
        resposta.data = {
            "detail": "Dados inválidos.",
            "code": "validacao",
            "campos": dados,
        }
    else:
        resposta.data = {"detail": str(dados), "code": codigo, "campos": {}}

    return resposta
