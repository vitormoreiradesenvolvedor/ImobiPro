from decimal import Decimal

import pytest

from apps.core.money import dinheiro, percentual, ratear


def test_dinheiro_arredonda_para_duas_casas():
    assert dinheiro("1234.567") == Decimal("1234.57")
    assert dinheiro(0.1 + 0.2) == Decimal("0.30")


def test_percentual_calcula_taxa_de_administracao():
    assert percentual("2500.00", "8") == Decimal("200.00")


def test_rateio_de_comissao_nao_perde_centavo():
    partes = ratear("1000.00", [40, 40, 20])

    assert sum(partes) == Decimal("1000.00")
    assert partes == [Decimal("400.00"), Decimal("400.00"), Decimal("200.00")]


def test_rateio_com_dizima_fecha_no_total():
    partes = ratear("100.00", [1, 1, 1])

    assert sum(partes) == Decimal("100.00")
    assert partes[-1] == Decimal("33.34")


def test_rateio_com_pesos_zerados_falha():
    with pytest.raises(ValueError):
        ratear("100.00", [0, 0])
