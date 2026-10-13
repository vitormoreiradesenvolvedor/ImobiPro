import factory

from apps.pessoas.models import Endereco, Pessoa, TipoPessoa

# CPFs/CNPJs com dígito verificador válido a API recusa documento inválido.
CPFS_VALIDOS = [
    "52998224725",
    "11144477735",
    "12345678909",
    "39053344705",
    "88350041502",
    "19100000000",
    "15350946056",
    "40442820135",
    "63017285003",
    "71428793860",
]
CNPJS_VALIDOS = [
    "11222333000181",
    "34028316000103",
    "60746948000112",
    "33000167000101",
    "47960950000121",
]


class EnderecoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Endereco

    cep = "37200000"
    logradouro = factory.Sequence(lambda n: f"Rua das Acácias {n}")
    numero = factory.Sequence(lambda n: str(100 + n))
    bairro = "Centro"
    cidade = "Lavras"
    uf = "MG"
    latitude = "-21.245000"
    longitude = "-44.999000"


class PessoaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pessoa

    tenant = None  # informado pelo teste
    tipo = TipoPessoa.FISICA
    nome = factory.Sequence(lambda n: f"Proprietário {n}")
    cpf_cnpj = factory.Sequence(lambda n: CPFS_VALIDOS[n % len(CPFS_VALIDOS)])
    email = factory.Sequence(lambda n: f"pessoa{n}@imobipro.test")
    telefone = "35998887777"
    endereco = factory.SubFactory(EnderecoFactory)
