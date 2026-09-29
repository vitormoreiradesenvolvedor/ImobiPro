from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from apps.contratos.models import Contrato, PapelParte, ParteContrato, TipoContrato


class ContratoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contrato

    tenant = None  # informado pelo teste
    numero = factory.Sequence(lambda n: f"LOC-2026-{n:04d}")
    tipo = TipoContrato.LOCACAO
    data_inicio = factory.LazyFunction(timezone.localdate)
    data_fim = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=900))
    # Decimal (não string): é o tipo que vem do banco e o que os cálculos usam.
    valor = Decimal("2500.00")
    dia_vencimento = 10
    taxa_administracao_percent = Decimal("8.00")
    taxa_intermediacao = Decimal("2500.00")
    multa_rescisoria_meses = 3


def montar_partes(contrato, locador, locatario):
    """Atalho: contrato de locação sem locador e locatário não ativa."""

    ParteContrato.objects.create(
        contrato=contrato, pessoa=locador, papel=PapelParte.LOCADOR
    )
    ParteContrato.objects.create(
        contrato=contrato, pessoa=locatario, papel=PapelParte.LOCATARIO
    )
    return contrato
