"""Cobranças do inquilino e repasses ao proprietário."""

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel, TenantBaseModel


class StatusCobranca(models.TextChoices):
    ABERTA = "ABERTA", "Aberta"
    PAGA = "PAGA", "Paga"
    ATRASADA = "ATRASADA", "Atrasada"
    CANCELADA = "CANCELADA", "Cancelada"


class FormaPagamento(models.TextChoices):
    PIX = "PIX", "Pix"
    BOLETO = "BOLETO", "Boleto"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferência"
    DINHEIRO = "DINHEIRO", "Dinheiro"
    CARTAO = "CARTAO", "Cartão"


class Cobranca(TenantBaseModel):
    """Uma competência mensal do contrato de locação."""

    contrato = models.ForeignKey(
        "contratos.Contrato", on_delete=models.CASCADE, related_name="cobrancas"
    )
    competencia = models.DateField("competência", help_text="Sempre o dia 1 do mês.")
    vencimento = models.DateField()

    valor_aluguel = models.DecimalField(max_digits=12, decimal_places=2)
    valor_condominio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_iptu = models.DecimalField(
        "valor do IPTU", max_digits=12, decimal_places=2, default=0
    )
    valor_seguro = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outros = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descricao_outros = models.CharField(max_length=140, blank=True)

    valor_multa = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_juros = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)

    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pago_em = models.DateField(null=True, blank=True)
    forma_pagamento = models.CharField(
        max_length=15, choices=FormaPagamento.choices, blank=True
    )

    status = models.CharField(
        max_length=10, choices=StatusCobranca.choices, default=StatusCobranca.ABERTA
    )
    nosso_numero = models.CharField(max_length=30, blank=True)
    linha_digitavel = models.CharField(max_length=60, blank=True)
    pix_copia_cola = models.TextField(blank=True)
    etapas_cobranca_enviadas = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "cobrança"
        verbose_name_plural = "cobranças"
        ordering = ["-competencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["contrato", "competencia"], name="cobranca_unica_por_competencia"
            )
        ]
        indexes = [
            models.Index(
                fields=["tenant", "status", "vencimento"], name="cobranca_status_venc"
            ),
        ]

    def __str__(self):
        return f"{self.contrato_id} {self.competencia:%m/%Y}: {self.valor_total}"

    @property
    def dias_de_atraso(self):
        if self.status == StatusCobranca.PAGA or self.status == StatusCobranca.CANCELADA:
            return 0
        return max(0, (timezone.localdate() - self.vencimento).days)

    @property
    def em_atraso(self):
        return self.dias_de_atraso > 0

    @property
    def saldo(self):
        from apps.core.money import dinheiro

        return dinheiro(self.valor_total - (self.valor_pago or 0))


class StatusRepasse(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    LIBERADO = "LIBERADO", "Liberado"
    PAGO = "PAGO", "Pago"
    CANCELADO = "CANCELADO", "Cancelado"


class Repasse(TenantBaseModel):
    """O que sobra para o proprietário depois da taxa e das retenções."""

    contrato = models.ForeignKey(
        "contratos.Contrato", on_delete=models.CASCADE, related_name="repasses"
    )
    cobranca = models.OneToOneField(
        Cobranca, on_delete=models.CASCADE, related_name="repasse", null=True, blank=True
    )
    competencia = models.DateField("competência")

    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2)
    taxa_administracao = models.DecimalField(max_digits=12, decimal_places=2)
    # [{"descricao": "Troca de chuveiro", "valor": "120.00"}]
    retencoes = models.JSONField("retenções", default=list, blank=True)
    valor_liquido = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=10, choices=StatusRepasse.choices, default=StatusRepasse.PENDENTE
    )
    pago_em = models.DateField(null=True, blank=True)
    comprovante = models.FileField(upload_to="repasses/", blank=True, null=True)

    class Meta:
        verbose_name = "repasse"
        verbose_name_plural = "repasses"
        ordering = ["-competencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["contrato", "competencia"], name="repasse_unico_por_competencia"
            )
        ]

    def __str__(self):
        return f"Repasse {self.competencia:%m/%Y} {self.valor_liquido}"

    @property
    def total_retencoes(self):
        from apps.core.money import dinheiro

        return dinheiro(sum(float(item.get("valor", 0)) for item in self.retencoes))


class EtapaReguaCobranca(models.TextChoices):
    LEMBRETE = "LEMBRETE", "Lembrete (D+1)"
    COBRANCA = "COBRANCA", "Cobrança (D+5)"
    AVISO_FORMAL = "AVISO_FORMAL", "Aviso formal (D+15)"
    JURIDICO = "JURIDICO", "Encaminhamento jurídico (D+30)"


# Dias de atraso que disparam cada etapa da régua (handoff §1.5).
REGUA_DE_COBRANCA = [
    (1, EtapaReguaCobranca.LEMBRETE),
    (5, EtapaReguaCobranca.COBRANCA),
    (15, EtapaReguaCobranca.AVISO_FORMAL),
    (30, EtapaReguaCobranca.JURIDICO),
]


class EventoCobranca(BaseModel):
    """Registro de cada disparo da régua prova do que foi comunicado."""

    cobranca = models.ForeignKey(Cobranca, on_delete=models.CASCADE, related_name="eventos")
    etapa = models.CharField(max_length=15, choices=EtapaReguaCobranca.choices)
    canal = models.CharField(max_length=20, default="EMAIL")
    destinatario = models.CharField(max_length=255, blank=True)
    detalhe = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "evento de cobrança"
        verbose_name_plural = "eventos de cobrança"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.etapa} {self.cobranca_id}"
