from django.db import models

from apps.core.models import TenantBaseModel


class TipoNotificacao(models.TextChoices):
    LEAD_NOVO = "LEAD_NOVO", "Lead novo atribuído"
    TICKET_NOVO = "TICKET_NOVO", "Pedido de visita pelo site"
    SLA_ESTOURANDO = "SLA_ESTOURANDO", "SLA de atendimento estourando"
    SLA_ESTOURADO = "SLA_ESTOURADO", "SLA de atendimento estourado"
    VISITA_HOJE = "VISITA_HOJE", "Visita agendada para hoje"
    PROPOSTA_RECEBIDA = "PROPOSTA_RECEBIDA", "Proposta recebida"
    PAGAMENTO_RECEBIDO = "PAGAMENTO_RECEBIDO", "Pagamento recebido"
    COBRANCA_ATRASADA = "COBRANCA_ATRASADA", "Cobrança atrasada"
    CONTRATO_A_VENCER = "CONTRATO_A_VENCER", "Contrato a vencer"
    EXCLUSIVIDADE_A_VENCER = "EXCLUSIVIDADE_A_VENCER", "Exclusividade a vencer"
    REAJUSTE_APLICADO = "REAJUSTE_APLICADO", "Reajuste aplicado"


class Notificacao(TenantBaseModel):
    """Aviso para um usuário. Nasce no banco e é empurrado pelo WebSocket."""

    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.CASCADE, related_name="notificacoes"
    )
    tipo = models.CharField(max_length=30, choices=TipoNotificacao.choices)
    titulo = models.CharField("título", max_length=140)
    descricao = models.CharField("descrição", max_length=255, blank=True)
    dados = models.JSONField(default=dict, blank=True)
    lida = models.BooleanField(default=False)
    lida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["usuario", "lida"], name="notificacao_usuario_lida"),
        ]

    def __str__(self):
        return f"{self.tipo}: {self.titulo}"
