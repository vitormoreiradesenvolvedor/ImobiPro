import factory

from apps.accounts.models import Papel, Tenant, Usuario


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant

    razao_social = factory.Sequence(lambda n: f"Imobiliária {n} Ltda")
    nome_fantasia = factory.Sequence(lambda n: f"Imob {n}")
    cnpj = factory.Sequence(lambda n: f"{n:014d}")
    subdominio = factory.Sequence(lambda n: f"imob-{n}")


class UsuarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    tenant = factory.SubFactory(TenantFactory)
    email = factory.Sequence(lambda n: f"corretor{n}@imobipro.test")
    nome_completo = factory.Sequence(lambda n: f"Corretor {n}")
    papel = Papel.CORRETOR

    @factory.post_generation
    def senha(usuario, create, valor, **kwargs):
        if not create:
            return
        usuario.set_password(valor or "senha-de-teste-123")
        usuario.save()
