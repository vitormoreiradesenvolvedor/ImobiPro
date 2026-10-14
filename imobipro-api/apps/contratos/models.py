"""Contratos de venda e locação, partes, comissões e reajustes."""

from datetime import timedelta

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Func, Q
from django.utils import timezone

from apps.core.models import BaseModel, SoftDeleteModel, TenantBaseModel


class TipoContrato(models.TextChoices):
    VENDA = "VENDA", "Venda"
    LOCACAO = "LOCACAO", "Locação"


class StatusContrato(models.TextChoices):
    RASCUNHO = "RASCUNHO", "Rascunho"
    ATIVO = "ATIVO", "Ativo"
    ENCERRADO = "ENCERRADO", "Encerrado"
    RESCINDIDO = "RESCINDIDO", "Rescindido"


class IndiceReajuste(models.TextChoices):
    IGPM = "IGPM", "IGP-M (FGV)"
    IPCA = "IPCA", "IPCA (IBGE)"
    INPC = "INPC", "INPC (IBGE)"
    SEM_REAJUSTE = "SEM_REAJUSTE", "Sem reajuste"


class TipoGarantia(models.TextChoices):
    FIADOR = "FIADOR", "Fiador"
    CAUCAO = "CAUCAO", "Caução"
    SEGURO_FIANCA = "SEGURO_FIANCA", "Seguro-fiança"
    TITULO_CAPITALIZACAO = "TITULO_CAPITALIZACAO", "Título de capitalização"
    SEM_GARANTIA = "SEM_GARANTIA", "Sem garantia"


class PapelParte(models.TextChoices):
    LOCADOR = "LOCADOR", "Locador"
    LOCATARIO = "LOCATARIO", "Locatário"
    FIADOR = "FIADOR", "Fiador"
    COMPRADOR = "COMPRADOR", "Comprador"
    VENDEDOR = "VENDEDOR", "Vendedor"


PAPEIS_POR_TIPO = {
    TipoContrato.LOCACAO: {PapelParte.LOCADOR, PapelParte.LOCATARIO, PapelParte.FIADOR},
    TipoContrato.VENDA: {PapelParte.COMPRADOR, PapelParte.VENDEDOR},
}

PRAZO_PADRAO_LOCACAO_MESES = 30


class Contrato(TenantBaseModel, SoftDeleteModel):
    numero = models.CharField("número", max_length=20, editable=False)
    tipo = models.CharField(max_length=10, choices=TipoContrato.choices)
    imovel = models.ForeignKey(
        "imoveis.Imovel",
        on_delete=models.PROTECT,
        related_name="contratos",
        verbose_name="imóvel",
    )
    proposta = models.ForeignKey(
        "crm.Proposta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contratos",
    )

    data_inicio = models.DateField("data de início")
    data_fim = models.DateField("data de término", null=True, blank=True)
    valor = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )

    # --- específicos de locação
    dia_vencimento = models.PositiveSmallIntegerField("dia de vencimento", default=10)
    indice_reajuste = models.CharField(
        max_length=15, choices=IndiceReajuste.choices, default=IndiceReajuste.IGPM
    )
    taxa_administracao_percent = models.DecimalField(
        "taxa de administração (%)", max_digits=5, decimal_places=2, default=8
    )
    taxa_intermediacao = models.DecimalField(
        "taxa de intermediação", max_digits=12, decimal_places=2, null=True, blank=True
    )
    garantia_tipo = models.CharField(
        "tipo de garantia",
        max_length=25,
        choices=TipoGarantia.choices,
        default=TipoGarantia.FIADOR,
    )
    garantia_valor = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    multa_rescisoria_meses = models.PositiveSmallIntegerField(
        "multa rescisória (meses)", default=3
    )
    multa_atraso_percent = models.DecimalField(
        "multa por atraso (%)", max_digits=5, decimal_places=2, default=2
    )
    juros_mora_mes_percent = models.DecimalField(
        "juros de mora ao mês (%)", max_digits=5, decimal_places=2, default=1
    )
    inclui_condominio = models.BooleanField("cobra condomínio junto", default=True)
    inclui_iptu = models.BooleanField("cobra IPTU junto", default=True)
    valor_seguro_incendio = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    status = models.CharField(
        max_length=12, choices=StatusContrato.choices, default=StatusContrato.RASCUNHO
    )
    arquivo_pdf = models.FileField(upload_to="contratos/", blank=True, null=True)
    assinado_em = models.DateField(null=True, blank=True)
    rescindido_em = models.DateField(null=True, blank=True)
    motivo_rescisao = models.CharField(max_length=255, blank=True)
    multa_rescisao_calculada = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        verbose_name = "contrato"
        verbose_name_plural = "contratos"
        ordering = ["-data_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "numero"], name="contrato_numero_unico_por_tenant"
            ),
            # Invariante do handoff §1.7.2: um imóvel não pode ter duas locações
            # ativas com períodos que se sobrepõem. A regra mora no banco porque
            # validação de aplicação não sobrevive a duas requisições simultâneas.
            ExclusionConstraint(
                name="locacao_sem_periodo_sobreposto",
                expressions=[
                    ("imovel", RangeOperators.EQUAL),
                    (
                        Func(
                            F("data_inicio"),
                            F("data_fim"),
                            function="daterange",
                            output_field=DateRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(tipo="LOCACAO", status="ATIVO", deletado_em__isnull=True),
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "status", "tipo"], name="contrato_tenant_status"
            ),
            models.Index(fields=["data_fim"], name="contrato_data_fim"),
        ]

    def __str__(self):
        return f"{self.numero} {self.get_tipo_display()} de {self.imovel_id}"

    @property
    def vigente(self):
        hoje = timezone.localdate()
        if self.status != StatusContrato.ATIVO:
            return False
        return self.data_inicio <= hoje and (self.data_fim is None or hoje <= self.data_fim)

    @property
    def dias_para_vencer(self):
        if not self.data_fim or self.status != StatusContrato.ATIVO:
            return None
        return (self.data_fim - timezone.localdate()).days

    @property
    def meses_restantes(self):
        dias = self.dias_para_vencer
        return max(0, round(dias / 30)) if dias is not None else None

    @property
    def prazo_total_meses(self):
        if not self.data_fim:
            return None
        return max(1, round((self.data_fim - self.data_inicio).days / 30))

    @property
    def proximo_reajuste_em(self):
        """12 meses após o início ou após o último reajuste aplicado."""
        if (
            self.tipo != TipoContrato.LOCACAO
            or self.indice_reajuste == IndiceReajuste.SEM_REAJUSTE
        ):
            return None
        ultimo = self.reajustes.order_by("-data_aplicacao").first()
        base = ultimo.data_aplicacao if ultimo else self.data_inicio
        return base + timedelta(days=365)

    def parte(self, papel):
        return self.partes.filter(papel=papel).select_related("pessoa").first()

    @property
    def locador(self):
        return self.parte(PapelParte.LOCADOR)

    @property
    def locatario(self):
        return self.parte(PapelParte.LOCATARIO)


class ParteContrato(BaseModel):
    """Quem assina. Percentual resolve imóvel com mais de um proprietário."""

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="partes")
    pessoa = models.ForeignKey(
        "pessoas.Pessoa", on_delete=models.PROTECT, related_name="contratos"
    )
    papel = models.CharField(max_length=12, choices=PapelParte.choices)
    percentual = models.DecimalField(max_digits=5, decimal_places=2, default=100)

    class Meta:
        verbose_name = "parte do contrato"
        verbose_name_plural = "partes do contrato"
        constraints = [
            models.UniqueConstraint(
                fields=["contrato", "pessoa", "papel"], name="parte_unica_por_papel"
            )
        ]

    def __str__(self):
        return f"{self.pessoa_id} como {self.get_papel_display()}"


class PapelComissao(models.TextChoices):
    CAPTADOR = "CAPTADOR", "Captador"
    VENDEDOR = "VENDEDOR", "Vendedor"
    IMOBILIARIA = "IMOBILIARIA", "Imobiliária"


class StatusComissao(models.TextChoices):
    PREVISTA = "PREVISTA", "Prevista"
    LIBERADA = "LIBERADA", "Liberada"
    PAGA = "PAGA", "Paga"
    CANCELADA = "CANCELADA", "Cancelada"


class ConfiguracaoComissao(BaseModel):
    """Tabela de comissão da imobiliária, editável em Configurações."""

    tenant = models.OneToOneField(
        "accounts.Tenant", on_delete=models.CASCADE, related_name="config_comissao"
    )
    percentual_venda = models.DecimalField(
        "comissão de venda (%)", max_digits=5, decimal_places=2, default=6
    )
    rateio_captador = models.DecimalField(
        "parte do captador (%)", max_digits=5, decimal_places=2, default=40
    )
    rateio_vendedor = models.DecimalField(
        "parte do vendedor (%)", max_digits=5, decimal_places=2, default=40
    )
    rateio_imobiliaria = models.DecimalField(
        "parte da imobiliária (%)", max_digits=5, decimal_places=2, default=20
    )

    class Meta:
        verbose_name = "configuração de comissão"
        verbose_name_plural = "configurações de comissão"

    def __str__(self):
        return f"Comissão de {self.tenant_id}: {self.percentual_venda}%"

    @property
    def rateio_soma_cem(self):
        return (
            self.rateio_captador + self.rateio_vendedor + self.rateio_imobiliaria
        ) == 100


class Comissao(TenantBaseModel):
    """Valor congelado no fechamento mudar a tabela não reescreve o passado."""

    contrato = models.ForeignKey(
        Contrato, on_delete=models.CASCADE, related_name="comissoes"
    )
    usuario = models.ForeignKey(
        "accounts.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comissoes",
    )
    papel = models.CharField(max_length=12, choices=PapelComissao.choices)
    percentual_snapshot = models.DecimalField(max_digits=5, decimal_places=2)
    base_calculo = models.DecimalField(max_digits=12, decimal_places=2)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=StatusComissao.choices, default=StatusComissao.PREVISTA
    )
    liberada_em = models.DateField(null=True, blank=True)
    paga_em = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "comissão"
        verbose_name_plural = "comissões"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["tenant", "status"], name="comissao_tenant_status"),
        ]

    def __str__(self):
        return f"{self.get_papel_display()} {self.valor}"


class Reajuste(BaseModel):
    contrato = models.ForeignKey(
        Contrato, on_delete=models.CASCADE, related_name="reajustes"
    )
    data_aplicacao = models.DateField()
    indice = models.CharField(max_length=15, choices=IndiceReajuste.choices)
    percentual = models.DecimalField(max_digits=6, decimal_places=3)
    valor_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    valor_novo = models.DecimalField(max_digits=12, decimal_places=2)
    aditivo_pdf = models.FileField(upload_to="contratos/aditivos/", blank=True, null=True)

    class Meta:
        verbose_name = "reajuste"
        verbose_name_plural = "reajustes"
        ordering = ["-data_aplicacao"]

    def __str__(self):
        return f"{self.indice} {self.percentual}% em {self.data_aplicacao}"
