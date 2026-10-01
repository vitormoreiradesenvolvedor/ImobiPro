"""Integrações com portais, PSP e WhatsApp."""

import secrets

from django.db import models

from apps.core.models import TenantBaseModel


class Portal(models.TextChoices):
    VIVA_REAL = "VIVA_REAL", "Viva Real"
    ZAP = "ZAP", "ZAP Imóveis"
    OLX = "OLX", "OLX"
    IMOVELWEB = "IMOVELWEB", "ImovelWeb"
    SITE_PROPRIO = "SITE_PROPRIO", "Site próprio"


class StatusEnvio(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    ENVIADO = "ENVIADO", "Enviado"
    ERRO = "ERRO", "Erro"
    DESCARTADO = "DESCARTADO", "Descartado"


def gerar_segredo():
    return secrets.token_urlsafe(32)


class IntegracaoPortal(TenantBaseModel):
    """Credencial e estado da integração com um portal."""

    portal = models.CharField(max_length=20, choices=Portal.choices)
    ativo = models.BooleanField(default=True)
    # Segredo compartilhado usado para assinar o webhook de entrada de leads.
    segredo_webhook = models.CharField(max_length=64, default=gerar_segredo)
    identificador_externo = models.CharField(max_length=120, blank=True)
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True)
    total_publicados = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "integração com portal"
        verbose_name_plural = "integrações com portais"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "portal"], name="integracao_unica_por_portal"
            )
        ]

    def __str__(self):
        return f"{self.get_portal_display()} {self.tenant_id}"


class EventoIntegracao(TenantBaseModel):
    """Log de tudo que entrou ou saiu. É o que permite reprocessar sem adivinhar."""

    portal = models.CharField(max_length=20, choices=Portal.choices, blank=True)
    direcao = models.CharField(
        max_length=10,
        choices=[("ENTRADA", "Entrada"), ("SAIDA", "Saída")],
        default="ENTRADA",
    )
    evento = models.CharField(max_length=60)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=12, choices=StatusEnvio.choices, default=StatusEnvio.PENDENTE
    )
    tentativas = models.PositiveSmallIntegerField(default=0)
    erro = models.TextField(blank=True)
    referencia = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "evento de integração"
        verbose_name_plural = "eventos de integração"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["tenant", "status"], name="evento_integracao_status"),
        ]

    def __str__(self):
        return f"{self.direcao} {self.evento} ({self.status})"
