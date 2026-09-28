"""Modelos base compartilhados por todos os apps de domínio."""

import uuid

from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """Chave UUID e carimbos de tempo em toda entidade do sistema."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantManager(models.Manager):
    """Manager padrão dos modelos multi-tenant.

    O filtro por tenant é responsabilidade da infraestrutura, nunca do
    desenvolvedor de feature ver ``apps.core.mixins.TenantQuerySetMixin``.
    """

    def do_tenant(self, tenant):
        return self.get_queryset().filter(tenant=tenant)


class TenantBaseModel(BaseModel):
    """Entidade pertencente a uma imobiliária (tenant)."""

    tenant = models.ForeignKey(
        "accounts.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        verbose_name="imobiliária",
    )

    objects = TenantManager()

    class Meta:
        abstract = True


class Acao(models.TextChoices):
    CRIACAO = "CREATE", "Criação"
    ALTERACAO = "UPDATE", "Alteração"
    EXCLUSAO = "DELETE", "Exclusão"


class LogAuditoria(TenantBaseModel):
    """Trilha de alteração de dado contratual e financeiro (handoff §1.7.6)."""

    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, related_name="auditorias"
    )
    modelo = models.CharField(max_length=64, db_index=True)
    objeto_id = models.CharField(max_length=64, db_index=True)
    acao = models.CharField(max_length=10, choices=Acao.choices)
    alteracoes = models.JSONField(default=dict)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "log de auditoria"
        verbose_name_plural = "logs de auditoria"
        ordering = ["-criado_em"]
        indexes = [models.Index(fields=["modelo", "objeto_id"], name="auditoria_objeto")]

    def __str__(self):
        return f"{self.acao} {self.modelo}#{self.objeto_id}"


class SoftDeleteQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(deletado_em__isnull=True)

    def delete(self):
        return self.update(deletado_em=timezone.now())


class SoftDeleteModel(models.Model):
    """Exclusão lógica: imóvel, contrato e pessoa nunca somem do banco."""

    deletado_em = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deletado_em = timezone.now()
        self.save(update_fields=["deletado_em"])

    def restaurar(self):
        self.deletado_em = None
        self.save(update_fields=["deletado_em"])
