from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.pessoas.models import Pessoa
from apps.pessoas.tests.factories import PessoaFactory

pytestmark = pytest.mark.django_db

PAYLOAD = {
    "tipo": "FISICA",
    "nome": "Joana Prado",
    "cpf_cnpj": "529.982.247-25",
    "telefone": "35998887777",
    "endereco": {
        "cep": "37200-000",
        "logradouro": "Rua São Paulo",
        "numero": "45",
        "bairro": "Centro",
        "cidade": "Lavras",
        "uf": "MG",
    },
}


def test_cria_pessoa_com_endereco_aninhado(api_autenticada):
    resposta = api_autenticada.post(reverse("pessoa-list"), PAYLOAD, format="json")

    assert resposta.status_code == 201
    pessoa = Pessoa.objects.get(pk=resposta.data["id"])
    assert pessoa.cpf_cnpj == "52998224725"  # normalizado, sem pontuação
    assert pessoa.endereco.cidade == "Lavras"
    assert pessoa.endereco.cep == "37200000"


def test_recusa_cpf_com_digito_verificador_invalido(api_autenticada):
    payload = {**PAYLOAD, "cpf_cnpj": "11111111111"}

    resposta = api_autenticada.post(reverse("pessoa-list"), payload, format="json")

    assert resposta.status_code == 400
    assert "CPF inválido" in str(resposta.data["campos"]["cpf_cnpj"])


def test_recusa_cnpj_invalido(api_autenticada):
    payload = {**PAYLOAD, "tipo": "JURIDICA", "cpf_cnpj": "11222333000199"}

    resposta = api_autenticada.post(reverse("pessoa-list"), payload, format="json")

    assert resposta.status_code == 400


def test_pessoa_juridica_exige_cnpj(api_autenticada):
    payload = {**PAYLOAD, "tipo": "JURIDICA"}

    resposta = api_autenticada.post(reverse("pessoa-list"), payload, format="json")

    assert resposta.status_code == 400
    assert "CNPJ" in str(resposta.data["campos"]["cpf_cnpj"])


def test_documento_duplicado_no_mesmo_tenant_falha(api_autenticada, tenant):
    PessoaFactory(tenant=tenant, cpf_cnpj="52998224725")

    resposta = api_autenticada.post(reverse("pessoa-list"), PAYLOAD, format="json")

    assert resposta.status_code == 400
    assert "Já existe" in str(resposta.data["campos"]["cpf_cnpj"])


def test_mesmo_documento_em_tenants_diferentes_e_permitido(api_autenticada, outro_tenant):
    PessoaFactory(tenant=outro_tenant, cpf_cnpj="52998224725")

    resposta = api_autenticada.post(reverse("pessoa-list"), PAYLOAD, format="json")

    assert resposta.status_code == 201


def test_atualiza_endereco_existente_sem_criar_outro(api_autenticada, proprietario):
    endereco_id = proprietario.endereco_id

    resposta = api_autenticada.patch(
        reverse("pessoa-detail", args=[proprietario.pk]),
        {
            "endereco": {
                "logradouro": "Rua Nova",
                "cidade": "Lavras",
                "uf": "MG",
                "numero": "900",
            }
        },
        format="json",
    )

    assert resposta.status_code == 200
    proprietario.refresh_from_db()
    assert proprietario.endereco_id == endereco_id
    assert proprietario.endereco.logradouro == "Rua Nova"


def test_exclusao_e_logica(api_autenticada, proprietario):
    resposta = api_autenticada.delete(reverse("pessoa-detail", args=[proprietario.pk]))

    assert resposta.status_code == 204
    proprietario.refresh_from_db()
    assert proprietario.deletado_em is not None
    assert api_autenticada.get(reverse("pessoa-list")).data["count"] == 0


def test_documento_de_pessoa_excluida_pode_ser_reaproveitado(api_autenticada, tenant):
    antiga = PessoaFactory(tenant=tenant, cpf_cnpj="52998224725")
    antiga.delete()

    resposta = api_autenticada.post(reverse("pessoa-list"), PAYLOAD, format="json")

    assert resposta.status_code == 201


def test_busca_por_nome_e_documento(api_autenticada, tenant):
    PessoaFactory(tenant=tenant, nome="Marcos Andrade", cpf_cnpj="11144477735")
    PessoaFactory(tenant=tenant, nome="Silvia Nunes", cpf_cnpj="12345678909")

    resposta = api_autenticada.get(reverse("pessoa-list"), {"search": "Marcos"})

    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["nome"] == "Marcos Andrade"


def test_pessoa_de_outro_tenant_nao_aparece(api_autenticada, outro_tenant):
    PessoaFactory(tenant=outro_tenant, nome="Invisível")

    assert api_autenticada.get(reverse("pessoa-list")).data["count"] == 0


@patch("apps.pessoas.services._buscar_na_viacep")
def test_consulta_cep_devolve_endereco_no_formato_do_modelo(mock_viacep, api_autenticada):
    mock_viacep.return_value = {
        "logradouro": "Praça Dr. Augusto Silva",
        "bairro": "Centro",
        "localidade": "Lavras",
        "uf": "MG",
    }

    resposta = api_autenticada.get(reverse("consulta-cep", args=["37200-000"]))

    assert resposta.status_code == 200
    assert resposta.data == {
        "cep": "37200000",
        "logradouro": "Praça Dr. Augusto Silva",
        "bairro": "Centro",
        "cidade": "Lavras",
        "uf": "MG",
    }


@patch("apps.pessoas.services._buscar_na_viacep")
def test_consulta_cep_usa_cache_na_segunda_chamada(mock_viacep, api_autenticada):
    mock_viacep.return_value = {
        "logradouro": "X",
        "bairro": "Y",
        "localidade": "Z",
        "uf": "MG",
    }

    api_autenticada.get(reverse("consulta-cep", args=["37200111"]))
    api_autenticada.get(reverse("consulta-cep", args=["37200111"]))

    assert mock_viacep.call_count == 1


@patch("apps.pessoas.services._buscar_na_viacep")
def test_cep_inexistente_retorna_404(mock_viacep, api_autenticada):
    mock_viacep.return_value = {"erro": True}

    resposta = api_autenticada.get(reverse("consulta-cep", args=["99999999"]))

    assert resposta.status_code == 404
    assert resposta.data["code"] == "cep_nao_encontrado"


def _imagem_minima():
    """PNG 1x1 válido, o suficiente para o ImageField aceitar o upload."""

    import base64

    from django.core.files.uploadedfile import SimpleUploadedFile

    conteudo = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    return SimpleUploadedFile("retrato.png", conteudo, content_type="image/png")


def test_cadastro_nasce_sem_foto(api_autenticada):
    resposta = api_autenticada.post(reverse("pessoa-list"), PAYLOAD, format="json")

    assert resposta.status_code == 201
    assert resposta.data["foto"] is None


def test_envia_e_remove_a_foto_do_cadastro(api_autenticada, proprietario):
    pessoa = proprietario
    url = reverse("pessoa-foto", args=[pessoa.id])

    envio = api_autenticada.post(url, {"foto": _imagem_minima()}, format="multipart")

    assert envio.status_code == 200
    assert envio.data["foto"]
    pessoa.refresh_from_db()
    assert pessoa.foto.name.startswith("pessoas/fotos/")

    remocao = api_autenticada.delete(url)

    assert remocao.status_code == 200
    pessoa.refresh_from_db()
    assert not pessoa.foto


def test_upload_sem_arquivo_avisa_em_vez_de_estourar(api_autenticada, proprietario):
    resposta = api_autenticada.post(
        reverse("pessoa-foto", args=[proprietario.id]), format="multipart"
    )

    assert resposta.status_code == 400
    assert "foto" in resposta.data["campos"]
