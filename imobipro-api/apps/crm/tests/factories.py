import factory
from django.utils import timezone

from apps.crm.models import EstagioLead, Lead, OrigemLead


class LeadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lead

    tenant = None  # informado pelo teste
    nome = factory.Sequence(lambda n: f"Interessado {n}")
    email = factory.Sequence(lambda n: f"lead{n}@cliente.test")
    telefone = "35991112222"
    origem = OrigemLead.SITE
    estagio = EstagioLead.NOVO
    valor_estimado = "350000.00"
    atribuido_em = factory.LazyFunction(timezone.now)
