"""Tenant (imobiliária) e Usuario base do isolamento multi-tenant."""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.core.models import BaseModel


class Plano(models.TextChoices):
    STARTER = "STARTER", "Starter (até 5 corretores)"
    PROFISSIONAL = "PROFISSIONAL", "Profissional (até 20 corretores)"
    ENTERPRISE = "ENTERPRISE", "Enterprise (ilimitado)"


class Papel(models.TextChoices):
    SUPERADMIN = "SUPERADMIN", "Superadministrador da plataforma"
    ADMIN = "ADMIN", "Administrador da imobiliária"
    GERENTE = "GERENTE", "Gerente"
    CORRETOR = "CORRETOR", "Corretor"
    FINANCEIRO = "FINANCEIRO", "Financeiro"
    PROPRIETARIO = "PROPRIETARIO", "Proprietário"
    INQUILINO = "INQUILINO", "Inquilino"


# Papéis que operam o painel interno da imobiliária.
PAPEIS_INTERNOS = {Papel.ADMIN, Papel.GERENTE, Papel.CORRETOR, Papel.FINANCEIRO}


class Tenant(BaseModel):
    """Uma imobiliária assinante. Raiz de todo isolamento de dados."""

    razao_social = models.CharField("razão social", max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True)
    cnpj = models.CharField(max_length=14, unique=True)
    creci = models.CharField("CRECI", max_length=20, blank=True)
    subdominio = models.SlugField("subdomínio", max_length=63, unique=True)
    plano = models.CharField(max_length=20, choices=Plano.choices, default=Plano.STARTER)
    ativo = models.BooleanField(default=True)
    logo = models.ImageField(upload_to="tenants/logos/", blank=True, null=True)
    cor_primaria = models.CharField(max_length=7, default="#0F766E")
    telefone = models.CharField(max_length=20, blank=True)
    email_contato = models.EmailField(blank=True)
    # Contador do código sequencial de imóvel (REF-000123) desta imobiliária.
    sequencia_imovel = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = "imobiliária"
        verbose_name_plural = "imobiliárias"
        ordering = ["razao_social"]

    def __str__(self):
        return f"{self.nome_fantasia or self.razao_social} ({self.subdominio})"


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("E-mail é obrigatório.")
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("papel", Papel.SUPERADMIN)
        extra.setdefault("tenant", None)

        if extra.get("is_staff") is not True:
            raise ValueError("Superusuário precisa de is_staff=True.")

        return self.create_user(email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin, BaseModel):
    """Operador do sistema. O SUPERADMIN da plataforma é o único sem tenant."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="usuarios",
        null=True,
        blank=True,
        verbose_name="imobiliária",
    )
    email = models.EmailField("e-mail", unique=True)
    nome_completo = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True)
    creci = models.CharField("CRECI", max_length=20, blank=True)
    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.CORRETOR)
    # Inquilino e proprietário são pessoas da carteira que ganharam acesso: o
    # vínculo é o que permite mostrar a cada um só o que é dele.
    pessoa = models.ForeignKey(
        "pessoas.Pessoa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acessos",
        verbose_name="cadastro vinculado",
    )
    avatar = models.ImageField(upload_to="usuarios/avatares/", blank=True, null=True)
    ativo = models.BooleanField(default=True)
    is_staff = models.BooleanField("acessa o admin", default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["nome_completo"]
        indexes = [
            models.Index(fields=["tenant", "papel", "ativo"], name="usuario_tenant_papel"),
        ]
        constraints = [
            # Só o superadministrador da plataforma pode existir sem tenant.
            models.CheckConstraint(
                condition=models.Q(papel="SUPERADMIN") | models.Q(tenant__isnull=False),
                name="usuario_nao_superadmin_exige_tenant",
            )
        ]

    def __str__(self):
        return f"{self.nome_completo} <{self.email}>"

    @property
    def is_active(self):
        """Django usa is_active no login; o campo de negócio é `ativo`."""
        return self.ativo

    @is_active.setter
    def is_active(self, valor):
        self.ativo = valor

    @property
    def is_superadmin(self):
        return self.papel == Papel.SUPERADMIN

    @property
    def eh_interno(self):
        return self.papel in PAPEIS_INTERNOS

    @property
    def primeiro_nome(self):
        return self.nome_completo.split(" ")[0]
