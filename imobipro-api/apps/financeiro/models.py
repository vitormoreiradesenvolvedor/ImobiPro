"""Lançamentos financeiros. Nada aqui é apagado só estornado."""

from django.db import models

from apps.core.models import TenantBaseModel


class TipoTransacao(models.TextChoices):
    RECEITA = "RECEITA", "Receita"
    DESPESA = "DESPESA", "Despesa"


class CategoriaFinanceira(models.TextChoices):
    ALUGUEL = "ALUGUEL", "Aluguel recebido"
    TAXA_ADMINISTRACAO = "TAXA_ADMINISTRACAO", "Taxa de administração"
    TAXA_INTERMEDIACAO = "TAXA_INTERMEDIACAO", "Taxa de intermediação"
    COMISSAO_VENDA = "COMISSAO_VENDA", "Comissão de venda"
    REPASSE_PROPRIETARIO = "REPASSE_PROPRIETARIO", "Repasse ao proprietário"
    CONDOMINIO = "CONDOMINIO", "Condomínio"
    IPTU = "IPTU", "IPTU"
    SEGURO = "SEGURO", "Seguro"
    MANUTENCAO = "MANUTENCAO", "Manutenção"
    MARKETING = "MARKETING", "Marketing"
    FOLHA = "FOLHA", "Folha e comissões"
    IMPOSTOS = "IMPOSTOS", "Impostos"
    OUTRAS_RECEITAS = "OUTRAS_RECEITAS", "Outras receitas"
    OUTRAS_DESPESAS = "OUTRAS_DESPESAS", "Outras despesas"


# Categorias que representam dinheiro de terceiros passando pela imobiliária:
# entram e saem, então não podem inflar o resultado do DRE.
CATEGORIAS_DE_PASSAGEM = {
    CategoriaFinanceira.CONDOMINIO,
    CategoriaFinanceira.IPTU,
    CategoriaFinanceira.REPASSE_PROPRIETARIO,
    CategoriaFinanceira.ALUGUEL,
}


class Transacao(TenantBaseModel):
    tipo = models.CharField(max_length=10, choices=TipoTransacao.choices)
    categoria = models.CharField(max_length=25, choices=CategoriaFinanceira.choices)
    descricao = models.CharField("descrição", max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)

    data_competencia = models.DateField()
    data_liquidacao = models.DateField(null=True, blank=True)

    cobranca = models.ForeignKey(
        "locacao.Cobranca",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transacoes",
    )
    repasse = models.ForeignKey(
        "locacao.Repasse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transacoes",
    )
    comissao = models.ForeignKey(
        "contratos.Comissao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transacoes",
    )
    contrato = models.ForeignKey(
        "contratos.Contrato",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transacoes",
    )

    estorno_de = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="estornos"
    )
    criado_por = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        verbose_name = "transação"
        verbose_name_plural = "transações"
        ordering = ["-data_competencia", "-criado_em"]
        indexes = [
            models.Index(
                fields=["tenant", "tipo", "data_competencia"], name="transacao_tenant_tipo"
            ),
            models.Index(fields=["categoria"], name="transacao_categoria"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.valor} {self.descricao}"

    @property
    def estornada(self):
        return self.estornos.exists()

    @property
    def eh_de_passagem(self):
        return self.categoria in CATEGORIAS_DE_PASSAGEM
