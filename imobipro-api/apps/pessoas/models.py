"""Pessoa (proprietário, inquilino, comprador, fiador) e Endereço."""

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel, SoftDeleteModel, TenantBaseModel


class UF(models.TextChoices):
    AC = "AC", "Acre"
    AL = "AL", "Alagoas"
    AP = "AP", "Amapá"
    AM = "AM", "Amazonas"
    BA = "BA", "Bahia"
    CE = "CE", "Ceará"
    DF = "DF", "Distrito Federal"
    ES = "ES", "Espírito Santo"
    GO = "GO", "Goiás"
    MA = "MA", "Maranhão"
    MT = "MT", "Mato Grosso"
    MS = "MS", "Mato Grosso do Sul"
    MG = "MG", "Minas Gerais"
    PA = "PA", "Pará"
    PB = "PB", "Paraíba"
    PR = "PR", "Paraná"
    PE = "PE", "Pernambuco"
    PI = "PI", "Piauí"
    RJ = "RJ", "Rio de Janeiro"
    RN = "RN", "Rio Grande do Norte"
    RS = "RS", "Rio Grande do Sul"
    RO = "RO", "Rondônia"
    RR = "RR", "Roraima"
    SC = "SC", "Santa Catarina"
    SP = "SP", "São Paulo"
    SE = "SE", "Sergipe"
    TO = "TO", "Tocantins"


class TipoPessoa(models.TextChoices):
    FISICA = "FISICA", "Pessoa física"
    JURIDICA = "JURIDICA", "Pessoa jurídica"


class EstadoCivil(models.TextChoices):
    SOLTEIRO = "SOLTEIRO", "Solteiro(a)"
    CASADO = "CASADO", "Casado(a)"
    DIVORCIADO = "DIVORCIADO", "Divorciado(a)"
    VIUVO = "VIUVO", "Viúvo(a)"
    UNIAO_ESTAVEL = "UNIAO_ESTAVEL", "União estável"


class Endereco(BaseModel):
    """Valor sempre acessado por Pessoa ou Imóvel não tem endpoint próprio."""

    cep = models.CharField(max_length=8, blank=True)
    logradouro = models.CharField(max_length=255)
    numero = models.CharField(max_length=20, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2, choices=UF.choices)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = "endereço"
        verbose_name_plural = "endereços"
        indexes = [models.Index(fields=["cidade", "bairro"], name="endereco_cidade_bairro")]

    def __str__(self):
        numero = self.numero or "s/n"
        return f"{self.logradouro}, {numero} {self.bairro}, {self.cidade}/{self.uf}"

    @property
    def geocodificado(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def resumo(self):
        return (
            f"{self.bairro}, {self.cidade}/{self.uf}"
            if self.bairro
            else f"{self.cidade}/{self.uf}"
        )


class Pessoa(TenantBaseModel, SoftDeleteModel):
    """Contraparte que não opera o sistema: proprietário, inquilino, fiador."""

    tipo = models.CharField(
        max_length=10, choices=TipoPessoa.choices, default=TipoPessoa.FISICA
    )
    nome = models.CharField(max_length=255)
    cpf_cnpj = models.CharField("CPF/CNPJ", max_length=14)
    rg_ie = models.CharField("RG/IE", max_length=20, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    estado_civil = models.CharField(max_length=15, choices=EstadoCivil.choices, blank=True)
    profissao = models.CharField("profissão", max_length=100, blank=True)
    renda_mensal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    # Foto do cadastro, sempre opcional: serve para o corretor reconhecer quem
    # chega para assinar, e o cadastro não pode travar por falta dela.
    foto = models.ImageField(upload_to="pessoas/fotos/", blank=True, null=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    endereco = models.ForeignKey(
        Endereco, on_delete=models.SET_NULL, null=True, blank=True, related_name="pessoas"
    )
    # Conta para repasse de aluguel: banco, agência, conta, tipo, chave Pix.
    dados_bancarios = models.JSONField(default=dict, blank=True)
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "cpf_cnpj"],
                condition=models.Q(deletado_em__isnull=True),
                name="pessoa_cpf_cnpj_unico_por_tenant",
            )
        ]
        indexes = [models.Index(fields=["tenant", "nome"], name="pessoa_tenant_nome")]

    def __str__(self):
        return self.nome

    @property
    def eh_juridica(self):
        return self.tipo == TipoPessoa.JURIDICA
