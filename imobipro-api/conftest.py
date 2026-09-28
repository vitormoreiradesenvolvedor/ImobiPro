import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Papel
from apps.accounts.tests.factories import TenantFactory, UsuarioFactory

SENHA = "senha-de-teste-123"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def tenant(db):
    return TenantFactory()


@pytest.fixture
def outro_tenant(db):
    return TenantFactory()


@pytest.fixture
def admin_imobiliaria(tenant):
    return UsuarioFactory(tenant=tenant, papel=Papel.ADMIN, senha=SENHA)


@pytest.fixture
def corretor(tenant):
    return UsuarioFactory(tenant=tenant, papel=Papel.CORRETOR, senha=SENHA)


@pytest.fixture
def gerente(tenant):
    return UsuarioFactory(tenant=tenant, papel=Papel.GERENTE, senha=SENHA)


@pytest.fixture
def financeiro(tenant):
    return UsuarioFactory(tenant=tenant, papel=Papel.FINANCEIRO, senha=SENHA)


@pytest.fixture
def api_autenticada(api, admin_imobiliaria):
    api.force_authenticate(user=admin_imobiliaria)
    return api


@pytest.fixture
def proprietario(tenant):
    from apps.pessoas.tests.factories import PessoaFactory

    return PessoaFactory(tenant=tenant)


@pytest.fixture
def imovel(tenant, proprietario, corretor):
    from apps.imoveis.tests.factories import ImovelFactory

    return ImovelFactory(tenant=tenant, proprietario=proprietario, captador=corretor)


@pytest.fixture
def imovel_publicavel(tenant, proprietario, corretor):
    """Imóvel que já cumpre todas as regras de publicação (5 fotos, geo, valores)."""
    from apps.imoveis.tests.factories import ImovelFactory

    return ImovelFactory(
        tenant=tenant, proprietario=proprietario, captador=corretor, com_fotos=5
    )
