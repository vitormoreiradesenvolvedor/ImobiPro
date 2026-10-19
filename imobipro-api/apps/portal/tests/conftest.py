"""Cenário mínimo do portal: um contrato assinado com locatário de verdade."""

import pytest

from apps.contratos.tests.factories import ContratoFactory, montar_partes
from apps.imoveis.services import publicar
from apps.pessoas.tests.factories import PessoaFactory


@pytest.fixture
def imovel_disponivel(imovel_publicavel):
    return publicar(imovel_publicavel)


@pytest.fixture
def locatario(tenant):
    return PessoaFactory(tenant=tenant, nome="Locatário do Portal")


@pytest.fixture
def contrato_pronto(tenant, imovel_disponivel, proprietario, locatario):
    contrato = ContratoFactory(tenant=tenant, imovel=imovel_disponivel)
    return montar_partes(contrato, proprietario, locatario)
