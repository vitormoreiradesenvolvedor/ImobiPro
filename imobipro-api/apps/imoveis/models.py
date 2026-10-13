"""Imóvel, fotos, características e histórico o núcleo da captação."""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel, SoftDeleteModel, TenantBaseModel

ROTULO_DESCRICAO = "descrição"


class TipoImovel(models.TextChoices):
    APARTAMENTO = "APARTAMENTO", "Apartamento"
    CASA = "CASA", "Casa"
    CASA_CONDOMINIO = "CASA_CONDOMINIO", "Casa em condomínio"
    COBERTURA = "COBERTURA", "Cobertura"
    KITNET = "KITNET", "Kitnet"
    TERRENO = "TERRENO", "Terreno"
    SALA_COMERCIAL = "SALA_COMERCIAL", "Sala comercial"
    GALPAO = "GALPAO", "Galpão"
    RURAL = "RURAL", "Área rural"


class Finalidade(models.TextChoices):
    VENDA = "VENDA", "Venda"
    LOCACAO = "LOCACAO", "Locação"
    VENDA_E_LOCACAO = "VENDA_E_LOCACAO", "Venda e locação"
    TEMPORADA = "TEMPORADA", "Temporada"


class SituacaoImovel(models.TextChoices):
    EM_CAPTACAO = "EM_CAPTACAO", "Em captação"
    DISPONIVEL = "DISPONIVEL", "Disponível"
    RESERVADO = "RESERVADO", "Reservado"
    VENDIDO = "VENDIDO", "Vendido"
    LOCADO = "LOCADO", "Locado"
    INATIVO = "INATIVO", "Inativo"


# Máquina de estados da situação do imóvel. Transição fora deste mapa é erro de
# negócio e é recusada no serviço, não só na interface.
TRANSICOES_PERMITIDAS = {
    SituacaoImovel.EM_CAPTACAO: {SituacaoImovel.DISPONIVEL, SituacaoImovel.INATIVO},
    SituacaoImovel.DISPONIVEL: {
        SituacaoImovel.RESERVADO,
        SituacaoImovel.VENDIDO,
        SituacaoImovel.LOCADO,
        SituacaoImovel.INATIVO,
    },
    SituacaoImovel.RESERVADO: {
        SituacaoImovel.DISPONIVEL,
        SituacaoImovel.VENDIDO,
        SituacaoImovel.LOCADO,
        SituacaoImovel.INATIVO,
    },
    SituacaoImovel.VENDIDO: {SituacaoImovel.INATIVO},
    SituacaoImovel.LOCADO: {SituacaoImovel.DISPONIVEL, SituacaoImovel.INATIVO},
    SituacaoImovel.INATIVO: {SituacaoImovel.DISPONIVEL, SituacaoImovel.EM_CAPTACAO},
}

MINIMO_DE_FOTOS_PARA_PUBLICAR = 5


class Caracteristica(BaseModel):
    """Catálogo global: piscina, elevador, portaria 24h, academia…"""

    nome = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    grupo = models.CharField(max_length=30, blank=True)  # imóvel, condomínio, lazer

    class Meta:
        verbose_name = "característica"
        verbose_name_plural = "características"
        ordering = ["grupo", "nome"]

    def __str__(self):
        return self.nome


class Imovel(TenantBaseModel, SoftDeleteModel):
    codigo = models.CharField("código", max_length=20, editable=False)
    titulo = models.CharField("título", max_length=160)
    descricao = models.TextField(ROTULO_DESCRICAO, blank=True)

    tipo = models.CharField(max_length=20, choices=TipoImovel.choices)
    finalidade = models.CharField(max_length=20, choices=Finalidade.choices)
    situacao = models.CharField(
        "situação",
        max_length=15,
        choices=SituacaoImovel.choices,
        default=SituacaoImovel.EM_CAPTACAO,
    )

    proprietario = models.ForeignKey(
        "pessoas.Pessoa",
        on_delete=models.PROTECT,
        related_name="imoveis",
        verbose_name="proprietário",
    )
    captador = models.ForeignKey(
        "accounts.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="imoveis_captados",
    )
    endereco = models.OneToOneField(
        "pessoas.Endereco",
        on_delete=models.PROTECT,
        related_name="imovel",
        verbose_name="endereço",
    )

    area_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_util = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quartos = models.PositiveSmallIntegerField(default=0)
    suites = models.PositiveSmallIntegerField("suítes", default=0)
    banheiros = models.PositiveSmallIntegerField(default=0)
    vagas = models.PositiveSmallIntegerField(default=0)
    andar = models.SmallIntegerField(null=True, blank=True)
    ano_construcao = models.PositiveSmallIntegerField(
        "ano de construção", null=True, blank=True
    )
    mobiliado = models.BooleanField(default=False)
    aceita_pet = models.BooleanField(default=False)

    valor_venda = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    valor_locacao = models.DecimalField(
        "valor de locação",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    valor_condominio = models.DecimalField(
        "valor do condomínio",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    valor_iptu_anual = models.DecimalField(
        "IPTU anual",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    parcelas_iptu = models.PositiveSmallIntegerField("parcelas do IPTU", default=10)

    matricula = models.CharField("matrícula", max_length=50, blank=True)
    inscricao_municipal = models.CharField("inscrição municipal", max_length=50, blank=True)
    exclusividade_ate = models.DateField("exclusividade até", null=True, blank=True)
    autorizacao_assinada = models.BooleanField(
        "autorização de venda assinada", default=False
    )

    caracteristicas = models.ManyToManyField(
        Caracteristica, blank=True, related_name="imoveis", verbose_name="características"
    )

    publicado_site = models.BooleanField("publicado no site", default=False)
    destaque = models.BooleanField(default=False)
    visualizacoes = models.PositiveIntegerField("visualizações", default=0)

    tour_360_url = models.URLField("tour 360°", blank=True)
    video_url = models.URLField("vídeo", blank=True)
    planta_baixa = models.FileField(upload_to="imoveis/plantas/", blank=True, null=True)

    # Índice de busca textual mantido pelo serviço `atualizar_indice_busca`.
    busca = SearchVectorField(null=True, editable=False)

    class Meta:
        verbose_name = "imóvel"
        verbose_name_plural = "imóveis"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "codigo"], name="imovel_codigo_unico_por_tenant"
            )
        ]
        indexes = [
            models.Index(
                fields=["tenant", "situacao", "finalidade"], name="imovel_tenant_sit_fin"
            ),
            models.Index(fields=["valor_locacao"], name="imovel_valor_locacao"),
            models.Index(fields=["valor_venda"], name="imovel_valor_venda"),
            GinIndex(fields=["busca"], name="imovel_busca_gin"),
        ]

    def __str__(self):
        return f"{self.codigo} {self.titulo}"

    @property
    def foto_capa(self):
        """Escolhe a capa em Python para aproveitar o prefetch da listagem.

        Filtrar no banco aqui custaria uma query por linha do grid é a origem
        clássica de N+1 nesta tela.
        """
        fotos = list(self.fotos.all())
        return next((foto for foto in fotos if foto.capa), fotos[0] if fotos else None)

    @property
    def total_fotos(self):
        return len(self.fotos.all())

    @property
    def valor_iptu_mensal(self):
        if not self.valor_iptu_anual or not self.parcelas_iptu:
            return None
        from apps.core.money import dinheiro

        return dinheiro(dinheiro(self.valor_iptu_anual) / self.parcelas_iptu)

    @property
    def disponivel_para_negocio(self):
        return self.situacao in {SituacaoImovel.DISPONIVEL, SituacaoImovel.RESERVADO}

    def pendencias_para_publicar(self):
        """Lista o que falta para o imóvel poder ir para o site/portais."""

        pendencias = []

        if self.total_fotos < MINIMO_DE_FOTOS_PARA_PUBLICAR:
            pendencias.append(
                f"Mínimo de {MINIMO_DE_FOTOS_PARA_PUBLICAR} fotos "
                f"(tem {self.total_fotos})."
            )
        if not self.endereco.geocodificado:
            pendencias.append("Endereço sem latitude/longitude.")
        if not self.proprietario_id:
            pendencias.append("Imóvel sem proprietário vinculado.")

        vende = self.finalidade in {Finalidade.VENDA, Finalidade.VENDA_E_LOCACAO}
        aluga = self.finalidade in {
            Finalidade.LOCACAO,
            Finalidade.VENDA_E_LOCACAO,
            Finalidade.TEMPORADA,
        }

        if vende and not self.valor_venda:
            pendencias.append("Valor de venda não informado.")
        if aluga and not self.valor_locacao:
            pendencias.append("Valor de locação não informado.")
        if aluga and not self.matricula:
            pendencias.append("Matrícula é obrigatória para locação.")

        return pendencias


class FotoImovel(BaseModel):
    imovel = models.ForeignKey(Imovel, on_delete=models.CASCADE, related_name="fotos")
    arquivo = models.ImageField(upload_to="imoveis/fotos/")
    arquivo_thumb = models.ImageField(upload_to="imoveis/thumbs/", blank=True, null=True)
    legenda = models.CharField(max_length=120, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)
    capa = models.BooleanField(default=False)

    class Meta:
        verbose_name = "foto"
        verbose_name_plural = "fotos"
        ordering = ["ordem", "criado_em"]

    def __str__(self):
        return f"Foto {self.ordem} de {self.imovel_id}"


class TipoMidia(models.TextChoices):
    BANNER = "BANNER", "Banner do anúncio"
    VIDEO = "VIDEO", "Vídeo"
    TOUR = "TOUR", "Tour virtual"
    PLANTA = "PLANTA", "Planta baixa"
    DOCUMENTO = "DOCUMENTO", "Documento do imóvel"


class MidiaImovel(BaseModel):
    """Banner, vídeo, planta e tour do anúncio.

    Fica separada de `FotoImovel` porque a galeria tem regra própria (capa,
    ordem, mínimo de cinco para publicar) e porque vídeo não é imagem: o mesmo
    campo não serve para os dois sem virar um monte de condicional.
    """

    imovel = models.ForeignKey(Imovel, on_delete=models.CASCADE, related_name="midias")
    tipo = models.CharField(max_length=12, choices=TipoMidia.choices)
    arquivo = models.FileField("arquivo", upload_to="imoveis/midias/")
    titulo = models.CharField(max_length=120, blank=True)
    descricao = models.TextField(ROTULO_DESCRICAO, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)
    destaque = models.BooleanField(
        "destaque",
        default=False,
        help_text="Banner marcado como destaque abre a página do imóvel no site.",
    )

    class Meta:
        verbose_name = "mídia"
        verbose_name_plural = "mídias"
        ordering = ["ordem", "criado_em"]
        indexes = [models.Index(fields=["imovel", "tipo"])]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.imovel_id}"


class TipoEventoImovel(models.TextChoices):
    CRIACAO = "CRIACAO", "Cadastro"
    VALOR = "VALOR", "Alteração de valor"
    SITUACAO = "SITUACAO", "Mudança de situação"
    PUBLICACAO = "PUBLICACAO", "Publicação"
    DESPUBLICACAO = "DESPUBLICACAO", "Despublicação"


class HistoricoImovel(BaseModel):
    """Linha do tempo mostrada na ficha do imóvel."""

    imovel = models.ForeignKey(Imovel, on_delete=models.CASCADE, related_name="historico")
    tipo = models.CharField(max_length=15, choices=TipoEventoImovel.choices)
    descricao = models.CharField(ROTULO_DESCRICAO, max_length=255)
    valor_anterior = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    valor_novo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        verbose_name = "evento do imóvel"
        verbose_name_plural = "histórico do imóvel"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.descricao}"
