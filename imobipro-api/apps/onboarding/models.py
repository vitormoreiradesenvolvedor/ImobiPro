"""Progresso do usuário no onboarding guiado."""

from django.db import models

from apps.core.models import TenantBaseModel


class ProgressoOnboarding(TenantBaseModel):
    """O que cada usuário já concluiu do tutorial.

    As missões não ficam aqui: elas são conferidas contra os dados reais da
    imobiliária a cada consulta (ver `apps.onboarding.missoes`). Isto guarda só
    o que é escolha do usuário tours já vistos e se ele dispensou o guia.
    """

    usuario = models.OneToOneField(
        "accounts.Usuario", on_delete=models.CASCADE, related_name="onboarding"
    )
    tours_concluidos = models.JSONField(default=list, blank=True)
    dispensado = models.BooleanField("dispensou o guia", default=False)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "progresso de onboarding"
        verbose_name_plural = "progressos de onboarding"

    def __str__(self):
        return f"Onboarding de {self.usuario_id}"

    def marcar_tour(self, identificador: str):
        if identificador not in self.tours_concluidos:
            self.tours_concluidos = [*self.tours_concluidos, identificador]
            self.save(update_fields=["tours_concluidos", "atualizado_em"])
        return self
