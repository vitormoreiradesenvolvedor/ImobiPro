"""Tickets de atendimento abertos pelo site.

O interessado não tem conta: ele pede uma visita pelo anúncio e passa a
acompanhar pelo número do protocolo. Do lado de dentro, o ticket é trabalho de
alguém, com prazo e histórico, e não um e-mail perdido na caixa de entrada.
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel, TenantBaseModel


class TipoTicket(models.TextChoices):
    VISITA = "VISITA", "Agendamento de visita"
    INFORMACAO = "INFORMACAO", "Pedido de informação"
    PROPOSTA = "PROPOSTA", "Interesse em proposta"
    MANUTENCAO = "MANUTENCAO", "Manutenção no imóvel"


class StatusTicket(models.TextChoices):
    ABERTO = "ABERTO", "Aberto"
    EM_ATENDIMENTO = "EM_ATENDIMENTO", "Em atendimento"
    AGENDADO = "AGENDADO", "Visita agendada"
    CONCLUIDO = "CONCLUIDO", "Concluído"
    CANCELADO = "CANCELADO", "Cancelado"


STATUS_ENCERRADOS = {StatusTicket.CONCLUIDO, StatusTicket.CANCELADO}

# Primeira resposta prometida ao interessado. O relógio é o mesmo argumento de
# venda do funil: quem responde primeiro fica com o cliente.
MINUTOS_SLA_PRIMEIRA_RESPOSTA = 30


class Ticket(TenantBaseModel):
    protocolo = models.CharField("protocolo", max_length=20, editable=False)
    tipo = models.CharField(max_length=12, choices=TipoTicket.choices)
    status = models.CharField(
        max_length=16, choices=StatusTicket.choices, default=StatusTicket.ABERTO
    )

    imovel = models.ForeignKey(
        "imoveis.Imovel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    lead = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    analista = models.ForeignKey(
        "accounts.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
        verbose_name="analista responsável",
    )

    solicitante_nome = models.CharField("nome", max_length=160)
    solicitante_email = models.EmailField("e-mail", blank=True)
    solicitante_telefone = models.CharField("telefone", max_length=20)
    mensagem = models.TextField(blank=True)

    # Preferência de visita: o interessado sugere, a imobiliária confirma.
    preferencia_data = models.DateField("data preferida", null=True, blank=True)
    preferencia_periodo = models.CharField(
        "período preferido",
        max_length=10,
        blank=True,
        choices=[("MANHA", "Manhã"), ("TARDE", "Tarde"), ("NOITE", "Noite")],
    )
    agendado_para = models.DateTimeField("agendado para", null=True, blank=True)

    primeira_resposta_em = models.DateTimeField(null=True, blank=True)
    encerrado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "ticket"
        verbose_name_plural = "tickets"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "protocolo"], name="ticket_protocolo_unico_por_tenant"
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "analista", "status"]),
            models.Index(fields=["protocolo"]),
        ]

    def __str__(self):
        return f"{self.protocolo} {self.get_tipo_display()}"

    @property
    def prazo_primeira_resposta(self):
        return self.criado_em + timedelta(minutes=MINUTOS_SLA_PRIMEIRA_RESPOSTA)

    @property
    def sla_estourado(self) -> bool:
        """Sem resposta dentro do prazo, e ainda em aberto."""

        if self.primeira_resposta_em or self.status in STATUS_ENCERRADOS:
            return False
        return timezone.now() > self.prazo_primeira_resposta

    @property
    def minutos_para_resposta(self):
        """Quanto falta (ou quanto passou, negativo) do prazo prometido."""

        if self.primeira_resposta_em or self.status in STATUS_ENCERRADOS:
            return None
        restante = self.prazo_primeira_resposta - timezone.now()
        return int(restante.total_seconds() // 60)


class EventoTicket(BaseModel):
    """Linha do tempo do atendimento. Nada é editado, tudo é acrescentado."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="eventos")
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True
    )
    descricao = models.CharField("descrição", max_length=255)
    visivel_ao_cliente = models.BooleanField(
        default=True,
        help_text="Nota interna fica fora do acompanhamento por protocolo.",
    )

    class Meta:
        verbose_name = "evento do ticket"
        verbose_name_plural = "eventos do ticket"
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.ticket_id}: {self.descricao[:40]}"
