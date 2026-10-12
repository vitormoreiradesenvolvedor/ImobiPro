"""O comando que zera a operação é destrutivo: precisa de rede de segurança."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.crm.tests.factories import LeadFactory
from apps.imoveis.models import Imovel
from apps.imoveis.tests.factories import ImovelFactory
from apps.pessoas.models import Pessoa

pytestmark = pytest.mark.django_db


def executar(*argumentos):
    saida = StringIO()
    call_command("limpar_operacao", *argumentos, stdout=saida)
    return saida.getvalue()


def test_sem_confirmar_nao_apaga_nada(tenant, proprietario, corretor):
    ImovelFactory(tenant=tenant, proprietario=proprietario)
    LeadFactory(tenant=tenant, corretor=corretor)

    saida = executar("--tenant", tenant.subdominio)

    assert "Nada foi apagado" in saida
    assert Imovel.objects.filter(tenant=tenant).count() == 1
    assert Pessoa.objects.filter(tenant=tenant).count() == 1


def test_com_confirmar_zera_a_operacao(tenant, proprietario, corretor):
    ImovelFactory(tenant=tenant, proprietario=proprietario, com_fotos=2)
    LeadFactory(tenant=tenant, corretor=corretor)

    saida = executar("--tenant", tenant.subdominio, "--confirmar")

    assert "pronta para uso real" in saida
    assert not Imovel.objects.filter(tenant=tenant).exists()
    assert not Pessoa.objects.filter(tenant=tenant).exists()


def test_equipe_e_imobiliaria_permanecem(tenant, admin_imobiliaria, proprietario):
    from apps.accounts.models import Tenant, Usuario

    ImovelFactory(tenant=tenant, proprietario=proprietario)

    executar("--tenant", tenant.subdominio, "--confirmar")

    assert Tenant.objects.filter(pk=tenant.pk).exists()
    assert Usuario.objects.filter(pk=admin_imobiliaria.pk).exists()


def test_codigo_do_imovel_volta_a_comecar_do_um(tenant, proprietario):
    from apps.imoveis.services import criar_imovel

    criar_imovel(
        {
            "titulo": "Primeiro",
            "tipo": "CASA",
            "finalidade": "VENDA",
            "proprietario": proprietario,
            "endereco": proprietario.endereco,
        },
        tenant,
    )
    executar("--tenant", tenant.subdominio, "--confirmar")

    from apps.pessoas.tests.factories import PessoaFactory

    novo_dono = PessoaFactory(tenant=tenant)
    novo = criar_imovel(
        {
            "titulo": "Depois da limpeza",
            "tipo": "CASA",
            "finalidade": "VENDA",
            "proprietario": novo_dono,
            "endereco": novo_dono.endereco,
        },
        tenant,
    )

    assert novo.codigo == "REF-000001"


def test_operacao_de_outra_imobiliaria_nao_e_tocada(tenant, outro_tenant, proprietario):
    from apps.pessoas.tests.factories import PessoaFactory

    ImovelFactory(tenant=tenant, proprietario=proprietario)
    alheio = ImovelFactory(
        tenant=outro_tenant, proprietario=PessoaFactory(tenant=outro_tenant)
    )

    executar("--tenant", tenant.subdominio, "--confirmar")

    assert Imovel.objects.filter(pk=alheio.pk).exists()
    assert not Imovel.objects.filter(tenant=tenant).exists()


def test_imobiliaria_inexistente_falha_com_mensagem_clara():
    with pytest.raises(CommandError, match="não encontrada"):
        executar("--tenant", "nao-existe", "--confirmar")


def test_limpeza_apaga_atendimento_candidatura_e_acesso_do_cliente(
    tenant, proprietario, corretor
):
    """Módulos novos entram na limpeza; senão o comando quebra no FK protegido."""

    from apps.accounts.models import Papel, Usuario
    from apps.atendimento.models import Ticket
    from apps.atendimento.services import abrir_ticket
    from apps.candidaturas.models import Candidatura
    from apps.candidaturas.services import abrir_candidatura
    from apps.imoveis.models import SituacaoImovel
    from apps.imoveis.services import mudar_situacao

    imovel = ImovelFactory(tenant=tenant, proprietario=proprietario, captador=corretor)
    mudar_situacao(imovel, SituacaoImovel.DISPONIVEL)

    abrir_ticket(
        {"solicitante_nome": "Marina", "solicitante_telefone": "35999990000"},
        tenant,
        imovel=imovel,
    )
    abrir_candidatura(
        {"pretendente_nome": "Marina", "pretendente_telefone": "35999990000"},
        tenant,
        imovel,
    )
    cliente = Usuario.objects.create_user(
        email="cliente@teste.local",
        password="senha-de-teste-123",
        nome_completo="Cliente",
        papel=Papel.INQUILINO,
        tenant=tenant,
        pessoa=proprietario,
    )

    executar("--tenant", tenant.subdominio, "--confirmar")

    assert not Ticket.objects.filter(tenant=tenant).exists()
    assert not Candidatura.objects.filter(tenant=tenant).exists()
    assert not Usuario.objects.filter(pk=cliente.pk).exists()
    # A equipe continua de pé.
    assert Usuario.objects.filter(pk=corretor.pk).exists()
