"""Ponto único de aritmética monetária.

Todo cálculo de aluguel, taxa, repasse e comissão passa por aqui. Dinheiro é
``Decimal`` com duas casas e arredondamento bancário nunca ``float``.
"""

from decimal import ROUND_HALF_EVEN, Decimal

CENTAVO = Decimal("0.01")


def dinheiro(valor) -> Decimal:
    """Normaliza qualquer entrada numérica para Decimal com 2 casas."""
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_EVEN)


def percentual(base, taxa) -> Decimal:
    """Aplica ``taxa`` (em %) sobre ``base``. Ex.: percentual(1000, 10) -> 100.00"""
    return dinheiro(Decimal(str(base)) * Decimal(str(taxa)) / Decimal("100"))


def ratear(valor, pesos: list) -> list:
    """Rateia ``valor`` pelos ``pesos`` sem perder centavo.

    A diferença de arredondamento é jogada na última parcela, de modo que a
    soma das partes seja sempre exatamente igual ao total.
    """
    total_pesos = sum(Decimal(str(p)) for p in pesos)
    if total_pesos == 0:
        raise ValueError("Soma dos pesos não pode ser zero.")

    valor = dinheiro(valor)
    partes = [dinheiro(valor * Decimal(str(peso)) / total_pesos) for peso in pesos[:-1]]
    partes.append(dinheiro(valor - sum(partes)))
    return partes
