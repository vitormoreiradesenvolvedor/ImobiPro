"""CRM: lead, interações, visitas e propostas o funil de vendas."""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel, TenantBaseModel

# SLA de primeiro atendimento vendido como diferencial do produto (handoff §1.4).
MINUTOS_SLA_PRIMEIRO_CONTATO = 15

# Referências preguiçosas a outros apps (evitam import circular).
MODELO_IMOVEL = "imoveis.Imovel"
MODELO_USUARIO = "accounts.Usuario"


class OrigemLead(models.TextChoices):
    SITE = "SITE", "Site próprio"
    PORTAL = "PORTAL", "Portal integrado"
    TELEFONE = "TELEFONE", "Telefone"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    INDICACAO = "INDICACAO", "Indicação"
    PLANTAO = "PLANTAO", "Plantão"
    PLACA = "PLACA", "Placa no imóvel"
    REDES_SOCIAIS = "REDES_SOCIAIS", "Redes sociais"


class EstagioLead(models.TextChoices):
    NOVO = "NOVO", "Novo"
    EM_CONTATO = "EM_CONTATO", "Em contato"
    QUALIFICADO = "QUALIFICADO", "Qualificado"
    VISITA_AGENDADA = "VISITA_AGENDADA", "Visita agendada"
    VISITA_REALIZADA = "VISITA_REALIZADA", "Visita realizada"
    PROPOSTA = "PROPOSTA", "Proposta"
    NEGOCIACAO = "NEGOCIACAO", "Negociação"
    FECHADO_GANHO = "FECHADO_GANHO", "Fechado ganho"
    FECHADO_PERDIDO = "FECHADO_PERDIDO", "Fechado perdido"


# Ordem das colunas do kanban.
ORDEM_DO_FUNIL = [
    EstagioLead.NOVO,
    EstagioLead.EM_CONTATO,
    EstagioLead.QUALIFICADO,
    EstagioLead.VISITA_AGENDADA,
    EstagioLead.VISITA_REALIZADA,
    EstagioLead.PROPOSTA,
    EstagioLead.NEGOCIACAO,
    EstagioLead.FECHADO_GANHO,
    EstagioLead.FECHADO_PERDIDO,
]

ESTAGIOS_FECHADOS = {EstagioLead.FECHADO_GANHO, EstagioLead.FECHADO_PERDIDO}


class MotivoPerda(models.TextChoices):
    PRECO = "PRECO", "Preço acima do esperado"
    LOCALIZACAO = "LOCALIZACAO", "Localização"
    CREDITO_NEGADO = "CREDITO_NEGADO", "Crédito negado"
    CONCORRENTE = "CONCORRENTE", "Comprou/alugou com concorrente"
    DESISTIU = "DESISTIU", "Desistiu da compra/locação"
    SEM_RETORNO = "SEM_RETORNO", "Não respondeu ao contato"
    IMOVEL_INDISPONIVEL = "IMOVEL_INDISPONIVEL", "Imóvel ficou indisponível"


class Temperatura(models.TextChoices):
    FRIO = "FRIO", "Frio"
    MORNO = "MORNO", "Morno"
    QUENTE = "QUENTE", "Quente"


class Lead(TenantBaseModel):
    nome = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    origem = models.CharField(max_length=20, choices=OrigemLead.choices)
    mensagem = models.TextField(blank=True)

    imovel_interesse = models.ForeignKey(
        MODELO_IMOVEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        verbose_name="imóvel de interesse",
    )
    corretor = models.ForeignKey(
        MODELO_USUARIO,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )

    estagio = models.CharField(
        "estágio", max_length=20, choices=EstagioLead.choices, default=EstagioLead.NOVO
    )
    temperatura = models.CharField(
        max_length=10, choices=Temperatura.choices, default=Temperatura.MORNO
    )
    valor_estimado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    motivo_perda = models.CharField(max_length=25, choices=MotivoPerda.choices, blank=True)
    observacao_perda = models.CharField(max_length=255, blank=True)

    primeiro_contato_em = models.DateTimeField(null=True, blank=True)
    sla_cumprido = models.BooleanField(null=True, blank=True)
    atribuido_em = models.DateTimeField(null=True, blank=True)
    fechado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "lead"
        verbose_name_plural = "leads"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(
                fields=["tenant", "estagio", "corretor"], name="lead_tenant_estagio"
            ),
            models.Index(fields=["tenant", "criado_em"], name="lead_tenant_criado"),
        ]

    def __str__(self):
        return f"{self.nome} ({self.get_estagio_display()})"

    @property
    def prazo_sla(self):
        base = self.atribuido_em or self.criado_em
        return base + timedelta(minutes=MINUTOS_SLA_PRIMEIRO_CONTATO) if base else None

    @property
    def minutos_para_sla(self):
        """Negativo quando o prazo já passou. É o que pinta o cartão de vermelho."""
        if self.primeiro_contato_em or not self.prazo_sla:
            return None
        return (self.prazo_sla - timezone.now()).total_seconds() / 60

    @property
    def sla_estourado(self):
        minutos = self.minutos_para_sla
        return minutos is not None and minutos < 0

    @property
    def esta_fechado(self):
        return self.estagio in ESTAGIOS_FECHADOS


class TipoInteracao(models.TextChoices):
    LIGACAO = "LIGACAO", "Ligação"
    EMAIL = "EMAIL", "E-mail"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    VISITA = "VISITA", "Visita"
    PROPOSTA = "PROPOSTA", "Proposta"
    NOTA = "NOTA", "Anotação"
    SISTEMA = "SISTEMA", "Evento do sistema"


class Interacao(BaseModel):
    """Linha do tempo do lead. Append-only: nada é editado nem apagado."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="interacoes")
    usuario = models.ForeignKey(
        MODELO_USUARIO, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    tipo = models.CharField(max_length=15, choices=TipoInteracao.choices)
    descricao = models.TextField("descrição")

    class Meta:
        verbose_name = "interação"
        verbose_name_plural = "interações"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.lead_id}"


class InteresseAposVisita(models.TextChoices):
    ALTO = "ALTO", "Quer fazer proposta"
    MEDIO = "MEDIO", "Vai pensar"
    BAIXO = "BAIXO", "Não gostou"


class Visita(TenantBaseModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="visitas")
    imovel = models.ForeignKey(
        MODELO_IMOVEL, on_delete=models.CASCADE, related_name="visitas"
    )
    corretor = models.ForeignKey(
        MODELO_USUARIO, on_delete=models.SET_NULL, null=True, related_name="visitas"
    )
    agendada_para = models.DateTimeField()
    realizada = models.BooleanField(default=False)
    cancelada = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    interesse_pos_visita = models.CharField(
        max_length=10, choices=InteresseAposVisita.choices, blank=True
    )

    class Meta:
        verbose_name = "visita"
        verbose_name_plural = "visitas"
        ordering = ["agendada_para"]
        indexes = [
            models.Index(fields=["tenant", "agendada_para"], name="visita_tenant_data"),
        ]

    def __str__(self):
        return f"{self.lead.nome} {self.agendada_para:%d/%m/%Y %H:%M}"

    @property
    def atrasada(self):
        return (
            not self.realizada
            and not self.cancelada
            and self.agendada_para < timezone.now()
        )


class StatusProposta(models.TextChoices):
    ENVIADA = "ENVIADA", "Enviada"
    EM_ANALISE = "EM_ANALISE", "Em análise"
    CONTRAPROPOSTA = "CONTRAPROPOSTA", "Contraproposta"
    ACEITA = "ACEITA", "Aceita"
    RECUSADA = "RECUSADA", "Recusada"
    EXPIRADA = "EXPIRADA", "Expirada"


class Proposta(TenantBaseModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="propostas")
    imovel = models.ForeignKey(
        MODELO_IMOVEL, on_delete=models.PROTECT, related_name="propostas"
    )
    valor_ofertado = models.DecimalField(max_digits=12, decimal_places=2)
    condicoes_pagamento = models.TextField("condições de pagamento", blank=True)
    validade = models.DateField()
    status = models.CharField(
        max_length=15, choices=StatusProposta.choices, default=StatusProposta.ENVIADA
    )
    observacao_resposta = models.CharField(max_length=255, blank=True)
    respondida_em = models.DateTimeField(null=True, blank=True)
    criada_por = models.ForeignKey(
        MODELO_USUARIO, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        verbose_name = "proposta"
        verbose_name_plural = "propostas"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Proposta de {self.valor_ofertado} em {self.imovel_id}"

    @property
    def expirada(self):
        return (
            self.status == StatusProposta.ENVIADA and self.validade < timezone.localdate()
        )

    @property
    def desconto_percentual(self):
        """Quanto a oferta está abaixo do anúncio argumento de negociação."""
        from apps.core.money import dinheiro

        anunciado = self.imovel.valor_venda or self.imovel.valor_locacao
        if not anunciado:
            return None
        return dinheiro((anunciado - self.valor_ofertado) / anunciado * 100)
