import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("imobipro")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # SLA de 15 minutos é o diferencial vendido: precisa de vigilância curta.
    "verificar-sla-de-atendimento": {
        "task": "crm.verificar_sla_de_atendimento",
        "schedule": crontab(minute="*/5"),
    },
    "avisar-sla-proximo-do-limite": {
        "task": "crm.avisar_sla_proximo_do_limite",
        "schedule": crontab(minute="*/5"),
    },
    "lembrar-visitas-do-dia": {
        "task": "crm.lembrar_visitas_do_dia",
        "schedule": crontab(hour=7, minute=30),
    },
    "expirar-propostas-vencidas": {
        "task": "crm.expirar_propostas_vencidas",
        "schedule": crontab(hour=0, minute=10),
    },
    "alertar-exclusividade-a-vencer": {
        "task": "imoveis.alertar_exclusividade_a_vencer",
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
    },
    # Locação: cobrança gerada com D-10 e régua de inadimplência diária.
    "gerar-cobrancas-mensais": {
        "task": "locacao.gerar_cobrancas_mensais",
        "schedule": crontab(hour=2, minute=0),
    },
    "marcar-cobrancas-atrasadas": {
        "task": "locacao.marcar_cobrancas_atrasadas",
        "schedule": crontab(hour=6, minute=0),
    },
    "executar-regua-de-inadimplencia": {
        "task": "locacao.executar_regua_de_inadimplencia",
        "schedule": crontab(hour=8, minute=0),
    },
    # Contratos: reajuste anual, aviso de vencimento e encerramento natural.
    "aplicar-reajustes-anuais": {
        "task": "contratos.aplicar_reajustes_anuais",
        "schedule": crontab(hour=3, minute=0),
    },
    "alertar-contratos-a-vencer": {
        "task": "contratos.alertar_contratos_a_vencer",
        "schedule": crontab(hour=8, minute=30),
    },
    "encerrar-contratos-vencidos": {
        "task": "contratos.encerrar_contratos_vencidos",
        "schedule": crontab(hour=4, minute=0),
    },
    # Integrações: carga incremental para os portais e fila de saída.
    "sincronizar-portais": {
        "task": "integracoes.sincronizar_portais",
        "schedule": crontab(minute="*/30"),
    },
    "processar-fila-de-saida": {
        "task": "integracoes.processar_fila_de_saida",
        "schedule": crontab(minute="*/10"),
    },
}
