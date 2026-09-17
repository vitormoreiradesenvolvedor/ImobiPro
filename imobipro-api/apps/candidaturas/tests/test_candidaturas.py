"""Candidatura: papelada, conferência e virada para contrato.

O pretendente não tem conta. O token do link é a credencial dele, e a análise
do outro lado é o que libera o contrato.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.candidaturas.models import (
    StatusCandidatura,
    StatusDocumento,
    TipoDocumento,
)
from apps.candidaturas.services import (
    RegraDeNegocio,
    abrir_candidatura,
    anexar_documento,
    aprovar,
    conferir_documento,
    gerar_contrato,
    mover_status,
)
from apps.imoveis.models import SituacaoImovel
from apps.imoveis.services import mudar_situacao

pytestmark = pytest.mark.django_db

PRETENDENTE = {
    "pretendente_nome": "Marina Interessada",
    "pretendente_cpf": "529.982.247-25",
    "pretendente_email": "marina@teste.local",
    "pretendente_telefone": "35991234567",
    "renda_mensal": Decimal("9000.00"),
    "ocupacao": "Analista",
}


def arquivo(nome="documento.pdf"):
    return SimpleUploadedFile(nome, b"conteudo", content_type="application/pdf")


@pytest.fixture
def disponivel(imovel):
    mudar_situacao(imovel, SituacaoImovel.DISPONIVEL)
    return imovel


@pytest.fixture
def candidatura(tenant, disponivel, corretor):
    return abrir_candidatura(dict(PRETENDENTE), tenant, disponivel, usuario=corretor)


def documentar(candidatura, tipos=None):
    for tipo in tipos or [
        TipoDocumento.IDENTIDADE,
        TipoDocumento.CPF,
        TipoDocumento.COMPROVANTE_RENDA,
        TipoDocumento.COMPROVANTE_RESIDENCIA,
    ]:
        anexar_documento(candidatura, tipo, arquivo())
    candidatura.refresh_from_db()
    return candidatura


def url_portal(tenant, token):
    return reverse(
        "candidatura-portal", kwargs={"subdominio": tenant.subdominio, "token": token}
    )


# --------------------------------------------------------------------- abertura


def test_candidatura_nasce_esperando_documentos(candidatura):
    assert candidatura.status == StatusCandidatura.RASCUNHO
    assert candidatura.protocolo.startswith("CAD-")
    assert len(candidatura.documentos_pendentes) == 4


def test_imovel_ja_locado_nao_aceita_candidatura(tenant, imovel, corretor):
    mudar_situacao(imovel, SituacaoImovel.DISPONIVEL)
    mudar_situacao(imovel, SituacaoImovel.LOCADO)

    with pytest.raises(RegraDeNegocio, match="locado"):
        abrir_candidatura(dict(PRETENDENTE), tenant, imovel, usuario=corretor)


def test_relacao_renda_aluguel_ajuda_a_decidir(candidatura, disponivel):
    disponivel.valor_locacao = Decimal("3000.00")
    disponivel.save(update_fields=["valor_locacao"])
    candidatura.refresh_from_db()

    assert candidatura.relacao_renda_aluguel == 3.0


# ------------------------------------------------------------ portal do cliente


def test_pretendente_ve_a_propria_candidatura_pelo_link(api, tenant, candidatura):
    resposta = api.get(url_portal(tenant, candidatura.token))

    assert resposta.status_code == 200
    assert resposta.data["protocolo"] == candidatura.protocolo
    assert len(resposta.data["documentos_pendentes"]) == 4


def test_link_invalido_nao_revela_nada(api, tenant, candidatura):
    resposta = api.get(url_portal(tenant, "token-que-nao-existe"))

    assert resposta.status_code == 404


def test_envio_pelo_link_dispensa_login(api, tenant, candidatura):
    resposta = api.post(
        url_portal(tenant, candidatura.token),
        {"tipo": TipoDocumento.IDENTIDADE, "arquivo": arquivo()},
        format="multipart",
    )

    assert resposta.status_code == 201
    assert candidatura.documentos.count() == 1


def test_documentacao_completa_manda_para_analise_sozinha(api, tenant, candidatura):
    """Ninguém precisa lembrar de mudar o status na mão."""

    for tipo in [
        TipoDocumento.IDENTIDADE,
        TipoDocumento.CPF,
        TipoDocumento.COMPROVANTE_RENDA,
        TipoDocumento.COMPROVANTE_RESIDENCIA,
    ]:
        api.post(
            url_portal(tenant, candidatura.token),
            {"tipo": tipo, "arquivo": arquivo()},
            format="multipart",
        )

    candidatura.refresh_from_db()
    assert candidatura.status == StatusCandidatura.EM_ANALISE


def test_nota_interna_nao_vaza_no_portal(api, tenant, candidatura, corretor):
    from apps.candidaturas.services import registrar_evento

    registrar_evento(
        candidatura, "Cliente parece apressado.", usuario=corretor, visivel_ao_cliente=False
    )

    resposta = api.get(url_portal(tenant, candidatura.token))

    textos = [evento["descricao"] for evento in resposta.data["eventos"]]
    assert "Cliente parece apressado." not in textos


# ------------------------------------------------------------------- conferência


def test_documento_recusado_precisa_de_motivo(candidatura, corretor):
    documentar(candidatura)
    documento = candidatura.documentos.first()

    with pytest.raises(RegraDeNegocio, match="errado"):
        conferir_documento(documento, aprovado=False, usuario=corretor)


def test_recusa_devolve_a_candidatura_para_o_cliente(candidatura, corretor):
    documentar(candidatura)
    documento = candidatura.documentos.first()

    conferir_documento(
        documento, aprovado=False, usuario=corretor, observacao="Foto ilegível."
    )
    candidatura.refresh_from_db()

    assert documento.status == StatusDocumento.RECUSADO
    assert candidatura.status == StatusCandidatura.PENDENTE
    assert TipoDocumento.IDENTIDADE in candidatura.documentos_pendentes


# ---------------------------------------------------------------------- decisão


def test_aprovacao_exige_documento_conferido(candidatura, corretor):
    documentar(candidatura)

    with pytest.raises(RegraDeNegocio, match="conferência"):
        aprovar(candidatura, usuario=corretor)


def test_aprovacao_cria_o_cadastro_da_pessoa(candidatura, corretor):
    documentar(candidatura)
    for documento in candidatura.documentos.all():
        conferir_documento(documento, aprovado=True, usuario=corretor)

    aprovar(candidatura, usuario=corretor)
    candidatura.refresh_from_db()

    assert candidatura.status == StatusCandidatura.APROVADA
    assert candidatura.pessoa is not None
    assert candidatura.pessoa.cpf_cnpj == "52998224725"


def test_aprovacao_reusa_pessoa_ja_cadastrada(candidatura, corretor, tenant):
    """Cliente antigo não vira cadastro duplicado."""

    from apps.pessoas.models import Pessoa

    # O cadastro antigo guarda só dígitos, como o resto do sistema.
    existente = Pessoa.objects.create(
        tenant=tenant, nome="Marina I.", cpf_cnpj="52998224725"
    )

    documentar(candidatura)
    for documento in candidatura.documentos.all():
        conferir_documento(documento, aprovado=True, usuario=corretor)
    aprovar(candidatura, usuario=corretor)
    candidatura.refresh_from_db()

    assert candidatura.pessoa == existente


def test_cpf_invalido_barra_a_aprovacao(tenant, disponivel, corretor):
    """Documento errado não vira cadastro: é o que a locação exige depois."""

    torta = abrir_candidatura(
        {**PRETENDENTE, "pretendente_cpf": "111.111.111-11"},
        tenant,
        disponivel,
        usuario=corretor,
    )
    documentar(torta)
    for documento in torta.documentos.all():
        conferir_documento(documento, aprovado=True, usuario=corretor)

    with pytest.raises(RegraDeNegocio, match="CPF"):
        aprovar(torta, usuario=corretor)


def test_candidatura_decidida_nao_volta_atras(candidatura, corretor):
    mover_status(
        candidatura, StatusCandidatura.DESISTIU, usuario=corretor, observacao="Desistiu."
    )

    with pytest.raises(RegraDeNegocio):
        mover_status(candidatura, StatusCandidatura.EM_ANALISE, usuario=corretor)


# ---------------------------------------------------------------------- contrato


def aprovada(candidatura, corretor):
    documentar(candidatura)
    for documento in candidatura.documentos.all():
        conferir_documento(documento, aprovado=True, usuario=corretor)
    aprovar(candidatura, usuario=corretor)
    candidatura.refresh_from_db()
    return candidatura


DADOS_CONTRATO = {
    "data_inicio": date.today(),
    "data_fim": date.today() + timedelta(days=365),
    "dia_vencimento": 10,
    "taxa_administracao_percent": Decimal("10.00"),
    "garantia_tipo": "CAUCAO",
    "garantia_valor": Decimal("5000.00"),
}


def test_contrato_nasce_com_locador_e_locatario(candidatura, corretor):
    pronta = aprovada(candidatura, corretor)

    contrato = gerar_contrato(pronta, dict(DADOS_CONTRATO), usuario=corretor)

    papeis = {parte.papel for parte in contrato.partes.all()}
    assert papeis == {"LOCADOR", "LOCATARIO"}
    assert contrato.imovel == pronta.imovel


def test_so_candidatura_aprovada_vira_contrato(candidatura, corretor):
    with pytest.raises(RegraDeNegocio, match="aprovada"):
        gerar_contrato(candidatura, dict(DADOS_CONTRATO), usuario=corretor)


def test_candidatura_nao_gera_dois_contratos(candidatura, corretor):
    pronta = aprovada(candidatura, corretor)
    gerar_contrato(pronta, dict(DADOS_CONTRATO), usuario=corretor)

    with pytest.raises(RegraDeNegocio, match="já gerou"):
        gerar_contrato(pronta, dict(DADOS_CONTRATO), usuario=corretor)


# ------------------------------------------------------------------ fila interna


def test_painel_mostra_onde_a_esteira_trava(api_autenticada, tenant, candidatura):
    resposta = api_autenticada.get(reverse("candidatura-painel"))

    assert resposta.status_code == 200
    assert resposta.data["aguardando_documentos"] == 1


def test_candidatura_de_outra_imobiliaria_nao_aparece(
    api_autenticada, outro_tenant, corretor
):
    from apps.imoveis.tests.factories import ImovelFactory
    from apps.pessoas.tests.factories import PessoaFactory

    alheio = ImovelFactory(
        tenant=outro_tenant, proprietario=PessoaFactory(tenant=outro_tenant)
    )
    mudar_situacao(alheio, SituacaoImovel.DISPONIVEL)
    abrir_candidatura(dict(PRETENDENTE), outro_tenant, alheio)

    resposta = api_autenticada.get(reverse("candidatura-list"))

    assert resposta.data["count"] == 0
