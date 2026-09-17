"""Candidatura à locação: a papelada entre o interesse e o contrato.

O pretendente não tem conta no sistema. Ele recebe um link com token, envia os
documentos por ali e acompanha a análise pelo mesmo link. Do lado de dentro,
cada documento é conferido item a item, e é essa conferência que libera o
contrato.
"""

import secrets

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel, TenantBaseModel

# Referência preguiçosa a outro app (evita import circular).
MODELO_USUARIO = "accounts.Usuario"


class StatusCandidatura(models.TextChoices):
    RASCUNHO = "RASCUNHO", "Aguardando documentos"
    EM_ANALISE = "EM_ANALISE", "Em análise"
    PENDENTE = "PENDENTE", "Pendência com o cliente"
    APROVADA = "APROVADA", "Aprovada"
    REPROVADA = "REPROVADA", "Reprovada"
    DESISTIU = "DESISTIU", "Cliente desistiu"


STATUS_ENCERRADOS = {
    StatusCandidatura.APROVADA,
    StatusCandidatura.REPROVADA,
    StatusCandidatura.DESISTIU,
}


class TipoDocumento(models.TextChoices):
    IDENTIDADE = "IDENTIDADE", "Documento de identidade"
    CPF = "CPF", "CPF"
    COMPROVANTE_RENDA = "COMPROVANTE_RENDA", "Comprovante de renda"
    COMPROVANTE_RESIDENCIA = "COMPROVANTE_RESIDENCIA", "Comprovante de residência"
    CERTIDAO_ESTADO_CIVIL = "CERTIDAO_ESTADO_CIVIL", "Certidão de estado civil"
    DOCUMENTO_FIADOR = "DOCUMENTO_FIADOR", "Documento do fiador"
    OUTRO = "OUTRO", "Outro documento"


# O que a imobiliária pede de todo pretendente. Fiador entra só quando a
# garantia escolhida é fiador, e por isso não está nesta lista.
DOCUMENTOS_OBRIGATORIOS = [
    TipoDocumento.IDENTIDADE,
    TipoDocumento.CPF,
    TipoDocumento.COMPROVANTE_RENDA,
    TipoDocumento.COMPROVANTE_RESIDENCIA,
]


class StatusDocumento(models.TextChoices):
    ENVIADO = "ENVIADO", "Enviado, aguardando conferência"
    APROVADO = "APROVADO", "Conferido"
    RECUSADO = "RECUSADO", "Recusado"


def gerar_token() -> str:
    """Token do link do pretendente. Longo o bastante para não ser adivinhado."""
    return secrets.token_urlsafe(32)


class Candidatura(TenantBaseModel):
    protocolo = models.CharField("protocolo", max_length=20, editable=False)
    token = models.CharField(max_length=64, default=gerar_token, editable=False)

    imovel = models.ForeignKey(
        "imoveis.Imovel", on_delete=models.PROTECT, related_name="candidaturas"
    )
    ticket = models.ForeignKey(
        "atendimento.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidaturas",
    )
    analista = models.ForeignKey(
        MODELO_USUARIO,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidaturas",
        verbose_name="analista responsável",
    )
    pessoa = models.ForeignKey(
        "pessoas.Pessoa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidaturas",
        help_text="Preenchido quando a candidatura é aprovada e vira contrato.",
    )
    contrato = models.ForeignKey(
        "contratos.Contrato",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidaturas",
    )

    pretendente_nome = models.CharField("nome", max_length=160)
    pretendente_cpf = models.CharField("CPF", max_length=14, blank=True)
    pretendente_email = models.EmailField("e-mail", blank=True)
    pretendente_telefone = models.CharField("telefone", max_length=20)
    renda_mensal = models.DecimalField(
        "renda mensal", max_digits=12, decimal_places=2, null=True, blank=True
    )
    ocupacao = models.CharField("ocupação", max_length=120, blank=True)
    observacoes = models.TextField("observações", blank=True)

    status = models.CharField(
        max_length=12, choices=StatusCandidatura.choices, default=StatusCandidatura.RASCUNHO
    )
    decidido_em = models.DateTimeField(null=True, blank=True)
    motivo_decisao = models.TextField("motivo da decisão", blank=True)

    class Meta:
        verbose_name = "candidatura"
        verbose_name_plural = "candidaturas"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "protocolo"],
                name="candidatura_protocolo_unico_por_tenant",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["token"]),
        ]

    def __str__(self):
        return f"{self.protocolo} {self.pretendente_nome}"

    @property
    def documentos_pendentes(self) -> list:
        """O que ainda falta para a análise poder começar.

        Consulta o banco em vez de percorrer o prefetch: logo depois de anexar
        um arquivo, a lista em memória ainda é a de antes do envio, e a
        candidatura ficaria presa em "aguardando documentos".
        """

        enviados = set(
            DocumentoCandidatura.objects.filter(candidatura=self)
            .exclude(status=StatusDocumento.RECUSADO)
            .values_list("tipo", flat=True)
        )
        return [tipo for tipo in DOCUMENTOS_OBRIGATORIOS if tipo not in enviados]

    @property
    def documentacao_completa(self) -> bool:
        return not self.documentos_pendentes

    @property
    def relacao_renda_aluguel(self):
        """Quantas vezes a renda cobre o aluguel. O mercado pede três."""

        aluguel = self.imovel.valor_locacao
        if not self.renda_mensal or not aluguel:
            return None
        return round(float(self.renda_mensal) / float(aluguel), 2)


class DocumentoCandidatura(BaseModel):
    candidatura = models.ForeignKey(
        Candidatura, on_delete=models.CASCADE, related_name="documentos"
    )
    tipo = models.CharField(max_length=24, choices=TipoDocumento.choices)
    arquivo = models.FileField(upload_to="candidaturas/documentos/")
    nome_original = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=10, choices=StatusDocumento.choices, default=StatusDocumento.ENVIADO
    )
    observacao = models.TextField("observação", blank=True)
    conferido_por = models.ForeignKey(
        MODELO_USUARIO, on_delete=models.SET_NULL, null=True, blank=True
    )
    conferido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "documento da candidatura"
        verbose_name_plural = "documentos da candidatura"
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.candidatura_id}"

    def conferir(self, aprovado: bool, usuario=None, observacao=""):
        self.status = StatusDocumento.APROVADO if aprovado else StatusDocumento.RECUSADO
        self.observacao = observacao
        self.conferido_por = usuario
        self.conferido_em = timezone.now()
        self.save(
            update_fields=[
                "status",
                "observacao",
                "conferido_por",
                "conferido_em",
                "atualizado_em",
            ]
        )
        return self


class EventoCandidatura(BaseModel):
    """Histórico da análise. Decisão de crédito precisa de rastro."""

    candidatura = models.ForeignKey(
        Candidatura, on_delete=models.CASCADE, related_name="eventos"
    )
    usuario = models.ForeignKey(
        MODELO_USUARIO, on_delete=models.SET_NULL, null=True, blank=True
    )
    descricao = models.CharField("descrição", max_length=255)
    visivel_ao_cliente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "evento da candidatura"
        verbose_name_plural = "eventos da candidatura"
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.candidatura_id}: {self.descricao[:40]}"
