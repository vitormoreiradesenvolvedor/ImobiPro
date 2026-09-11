"""Catálogo padrão de características base dos filtros de busca."""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.imoveis.models import Caracteristica

CATALOGO = {
    "Imóvel": [
        "Armários embutidos",
        "Ar-condicionado",
        "Varanda",
        "Varanda gourmet",
        "Suíte máster",
        "Closet",
        "Lavabo",
        "Área de serviço",
        "Despensa",
        "Aquecimento solar",
        "Mobiliado",
        "Sacada",
        "Escritório",
    ],
    "Condomínio": [
        "Portaria 24h",
        "Elevador",
        "Interfone",
        "Circuito de segurança",
        "Vaga coberta",
        "Gás encanado",
        "Gerador",
    ],
    "Lazer": [
        "Piscina",
        "Churrasqueira",
        "Academia",
        "Salão de festas",
        "Playground",
        "Quadra poliesportiva",
        "Sauna",
        "Espaço pet",
    ],
}


class Command(BaseCommand):
    help = "Popula o catálogo global de características de imóvel."

    def handle(self, *args, **options):
        criadas = 0
        for grupo, nomes in CATALOGO.items():
            for nome in nomes:
                _, nova = Caracteristica.objects.get_or_create(
                    slug=slugify(nome), defaults={"nome": nome, "grupo": grupo}
                )
                criadas += int(nova)

        total = Caracteristica.objects.count()
        self.stdout.write(self.style.SUCCESS(f"{criadas} novas · {total} no catálogo."))
