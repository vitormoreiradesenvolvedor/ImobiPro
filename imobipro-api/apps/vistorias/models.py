"""Vistorias de entrada, periódica e saída.

O comparativo entrada × saída é o documento que resolve disputa de caução
por isso cada item guarda estado e fotos dos dois momentos.
"""

from django.db import models

from apps.core.models import BaseModel, TenantBaseModel


class TipoVistoria(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    PERIODICA = "PERIODICA", "Periódica"
    SAIDA = "SAIDA", "Saída"


class StatusVistoria(models.TextChoices):
    RASCUNHO = "RASCUNHO", "Em preenchimento"
    FINALIZADA = "FINALIZADA", "Finalizada"


class EstadoItem(models.TextChoices):
    OTIMO = "OTIMO", "Ótimo"
    BOM = "BOM", "Bom"
    REGULAR = "REGULAR", "Regular"
    RUIM = "RUIM", "Ruim"
    AUSENTE = "AUSENTE", "Ausente"


# Peso usado para comparar entrada e saída: queda de estado vira apontamento.
ORDEM_DOS_ESTADOS = {
    EstadoItem.OTIMO: 4,
    EstadoItem.BOM: 3,
    EstadoItem.REGULAR: 2,
    EstadoItem.RUIM: 1,
    EstadoItem.AUSENTE: 0,
}

ILUMINACAO = "Iluminação"

# Checklist padrão sugerido ao abrir uma vistoria.
CHECKLIST_PADRAO = {
    "Sala": ["Piso", "Paredes", "Teto", "Janelas", ILUMINACAO, "Tomadas"],
    "Cozinha": ["Piso", "Armários", "Pia", "Torneira", "Azulejos", ILUMINACAO],
    "Quarto": ["Piso", "Paredes", "Armários", "Janelas", ILUMINACAO],
    "Banheiro": ["Vaso sanitário", "Pia", "Box", "Chuveiro", "Azulejos", "Ventilação"],
    "Área de serviço": ["Tanque", "Torneira", "Piso", "Ponto de máquina"],
    "Geral": ["Chaves", "Medidor de água", "Medidor de energia", "Pintura", "Portas"],
}


class Vistoria(TenantBaseModel):
    contrato = models.ForeignKey(
        "contratos.Contrato", on_delete=models.CASCADE, related_name="vistorias"
    )
    tipo = models.CharField(max_length=10, choices=TipoVistoria.choices)
    status = models.CharField(
        max_length=12, choices=StatusVistoria.choices, default=StatusVistoria.RASCUNHO
    )
    realizada_em = models.DateField()
    vistoriador = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, related_name="vistorias"
    )
    observacoes_gerais = models.TextField("observações gerais", blank=True)
    laudo_pdf = models.FileField(upload_to="vistorias/laudos/", blank=True, null=True)
    assinatura_locatario = models.BooleanField("assinado pelo locatário", default=False)
    assinatura_imobiliaria = models.BooleanField("assinado pela imobiliária", default=False)
    finalizada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "vistoria"
        verbose_name_plural = "vistorias"
        ordering = ["-realizada_em"]
        constraints = [
            # Entrada e saída acontecem uma única vez por contrato.
            models.UniqueConstraint(
                fields=["contrato", "tipo"],
                condition=models.Q(tipo__in=["ENTRADA", "SAIDA"]),
                name="vistoria_entrada_saida_unica",
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.contrato_id}"

    @property
    def total_itens(self):
        return self.itens.count()

    @property
    def itens_com_problema(self):
        return self.itens.filter(estado__in=[EstadoItem.RUIM, EstadoItem.AUSENTE]).count()

    @property
    def assinada(self):
        return self.assinatura_locatario and self.assinatura_imobiliaria


class ItemVistoria(BaseModel):
    vistoria = models.ForeignKey(Vistoria, on_delete=models.CASCADE, related_name="itens")
    comodo = models.CharField("cômodo", max_length=60)
    item = models.CharField(max_length=80)
    estado = models.CharField(max_length=10, choices=EstadoItem.choices)
    observacao = models.CharField("observação", max_length=255, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "item de vistoria"
        verbose_name_plural = "itens de vistoria"
        ordering = ["comodo", "ordem", "item"]
        constraints = [
            models.UniqueConstraint(
                fields=["vistoria", "comodo", "item"], name="item_unico_por_comodo"
            )
        ]

    def __str__(self):
        return f"{self.comodo} / {self.item}: {self.get_estado_display()}"

    @property
    def peso(self):
        return ORDEM_DOS_ESTADOS.get(self.estado, 0)


class FotoItemVistoria(BaseModel):
    item = models.ForeignKey(ItemVistoria, on_delete=models.CASCADE, related_name="fotos")
    arquivo = models.ImageField(upload_to="vistorias/fotos/")
    legenda = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "foto do item"
        verbose_name_plural = "fotos do item"

    def __str__(self):
        return f"Foto de {self.item_id}"
