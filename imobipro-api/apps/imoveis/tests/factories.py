from decimal import Decimal
from io import BytesIO

import factory
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.imoveis.models import (
    Caracteristica,
    Finalidade,
    FotoImovel,
    Imovel,
    SituacaoImovel,
    TipoImovel,
)
from apps.pessoas.tests.factories import EnderecoFactory, PessoaFactory


def imagem_de_teste(nome="foto.png", cor=(120, 160, 200)):
    """PNG mínimo em memória não depende de arquivo no disco."""
    buffer = BytesIO()
    Image.new("RGB", (40, 30), cor).save(buffer, format="PNG")
    return SimpleUploadedFile(nome, buffer.getvalue(), content_type="image/png")


class CaracteristicaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Caracteristica
        django_get_or_create = ["slug"]

    nome = factory.Sequence(lambda n: f"Característica {n}")
    slug = factory.Sequence(lambda n: f"caracteristica-{n}")
    grupo = "Lazer"


class ImovelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Imovel

    tenant = None  # informado pelo teste
    codigo = factory.Sequence(lambda n: f"REF-{n:06d}")
    titulo = factory.Sequence(lambda n: f"Apartamento {n} no Centro")
    descricao = "Imóvel amplo, com sol da manhã e vista livre."
    tipo = TipoImovel.APARTAMENTO
    finalidade = Finalidade.LOCACAO
    situacao = SituacaoImovel.EM_CAPTACAO
    proprietario = factory.SubFactory(PessoaFactory)
    endereco = factory.SubFactory(EnderecoFactory)
    quartos = 2
    banheiros = 1
    vagas = 1
    # Decimal, como vem do banco string aqui esconde erro de aritmética.
    area_util = Decimal("68.00")
    valor_locacao = Decimal("2500.00")
    valor_condominio = Decimal("480.00")
    valor_iptu_anual = Decimal("1200.00")
    matricula = "12345"

    @factory.post_generation
    def com_fotos(imovel, create, quantidade, **kwargs):
        if not create or not quantidade:
            return
        for i in range(quantidade):
            FotoImovel.objects.create(
                imovel=imovel,
                arquivo=imagem_de_teste(f"foto{i}.png"),
                ordem=i,
                capa=(i == 0),
            )
