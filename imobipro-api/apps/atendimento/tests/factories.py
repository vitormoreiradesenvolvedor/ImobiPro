import factory

from apps.atendimento.models import Ticket, TipoTicket


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    tipo = TipoTicket.VISITA
    protocolo = factory.Sequence(lambda n: f"ATD-2026-{n:06d}")
    solicitante_nome = factory.Faker("name", locale="pt_BR")
    solicitante_telefone = "35991234567"
    solicitante_email = factory.Faker("email")
    mensagem = "Tenho interesse em visitar."
