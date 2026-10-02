"""Cenário de demonstração: dois pedidos de visita, uma candidatura e o portal.

Roda depois de `semear_operacao --completo`:

    docker compose exec -T api python manage.py shell < cenario_demonstracao.py

Existe porque a massa semeada é a operação em regime, e a demonstração precisa
das telas com trabalho em aberto: fila de atendimento com prazo correndo,
documento recusado esperando reenvio e um inquilino com acesso ao portal.
"""

import secrets
from pathlib import Path

from django.core.files.base import ContentFile

from apps.accounts.models import Papel, Tenant, Usuario
from apps.atendimento.services import abrir_ticket
from apps.candidaturas.models import DOCUMENTOS_OBRIGATORIOS
from apps.candidaturas.services import abrir_candidatura, anexar_documento, conferir_documento
from apps.contratos.models import Contrato, PapelParte, StatusContrato
from apps.imoveis.models import Imovel

tenant = Tenant.objects.get(subdominio="horizonte")
imoveis = list(Imovel.objects.filter(tenant=tenant, publicado_site=True).order_by("codigo"))

primeiro = abrir_ticket(
    {
        "tipo": "VISITA",
        "solicitante_nome": "Rodrigo Ferraz",
        "solicitante_telefone": "35991110022",
        "solicitante_email": "rodrigo@cliente.test",
        "preferencia_periodo": "MANHA",
        "mensagem": "Posso visitar ainda esta semana?",
    },
    tenant,
    imovel=imoveis[0],
)
segundo = abrir_ticket(
    {
        "tipo": "VISITA",
        "solicitante_nome": "Marina Interessada",
        "solicitante_telefone": "35991234567",
        "solicitante_email": "marina@cliente.test",
        "preferencia_periodo": "TARDE",
        "mensagem": "Aceita pet?",
    },
    tenant,
    imovel=imoveis[-1],
)

analista = Usuario.objects.filter(tenant=tenant, papel=Papel.CORRETOR).first()
candidatura = abrir_candidatura(
    {
        "pretendente_nome": "Marina Interessada",
        "pretendente_cpf": "529.982.247-25",
        "pretendente_email": "marina@cliente.test",
        "pretendente_telefone": "35991234567",
        "renda_mensal": 9000,
        "ocupacao": "Analista de sistemas",
    },
    tenant,
    segundo.imovel,
    ticket=segundo,
    usuario=analista,
)

amostra = Path("apps/core/seed/fotos/imovel1-fachada.jpg").read_bytes()
for tipo in DOCUMENTOS_OBRIGATORIOS:
    anexar_documento(
        candidatura, tipo, ContentFile(amostra, name=f"{tipo.lower()}.jpg"), f"{tipo}.jpg"
    )
conferir_documento(
    candidatura.documentos.filter(tipo=DOCUMENTOS_OBRIGATORIOS[0]).first(),
    False,
    usuario=analista,
    observacao="Foto ilegível, reenvie o documento inteiro.",
)

contrato = (
    Contrato.objects.filter(tenant=tenant, status=StatusContrato.ATIVO).order_by("numero").first()
)
pessoa = contrato.partes.filter(papel=PapelParte.LOCATARIO).first().pessoa
senha = secrets.token_urlsafe(9)
usuario = Usuario.objects.filter(email__iexact=pessoa.email).first() or Usuario(
    tenant=tenant, email=pessoa.email, nome_completo=pessoa.nome, papel=Papel.INQUILINO
)
usuario.pessoa = pessoa
usuario.set_password(senha)
usuario.save()

candidatura.refresh_from_db()
print("tickets:", primeiro.protocolo, segundo.protocolo)
print("candidatura:", candidatura.protocolo, "|", candidatura.get_status_display())
print("link: http://localhost:8080/candidatura/horizonte/" + candidatura.token)
print("contrato:", contrato.numero, "| acesso:", usuario.email, senha)
