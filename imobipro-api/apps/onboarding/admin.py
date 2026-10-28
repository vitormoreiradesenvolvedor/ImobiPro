from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.onboarding.models import ProgressoOnboarding


@admin.register(ProgressoOnboarding)
class ProgressoOnboardingAdmin(ModelAdmin):
    list_display = ["usuario", "dispensado", "concluido_em", "atualizado_em"]
    list_filter = ["dispensado", "tenant"]
