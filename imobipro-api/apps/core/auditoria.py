"""Helpers de gravação da trilha de auditoria.

O modelo vive em ``apps.core.models.LogAuditoria``; aqui fica só a mecânica de
capturar autor, IP e diferença entre antes e depois.
"""

from apps.core.models import Acao, LogAuditoria

__all__ = ["Acao", "LogAuditoria", "registrar", "diferenca", "ip_do_request", "snapshot"]


def ip_do_request(request):
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def snapshot(instancia, campos):
    """Fotografia dos campos que interessam à auditoria, já serializável."""
    return {campo: str(getattr(instancia, campo, None)) for campo in campos}


def diferenca(antes: dict, depois: dict) -> dict:
    """Só os campos que realmente mudaram log enxuto é log lido."""
    return {
        campo: {"de": antes.get(campo), "para": depois.get(campo)}
        for campo in depois
        if str(antes.get(campo)) != str(depois.get(campo))
    }


def registrar(instancia, acao, request=None, antes=None, depois=None, tenant=None):
    """Grava uma entrada de auditoria e devolve o log criado (ou None)."""

    from apps.core.middleware import tenant_do_request

    tenant = tenant or getattr(instancia, "tenant", None)
    if request is not None and tenant is None:
        tenant = tenant_do_request(request)
    if tenant is None:
        return None

    usuario = getattr(request, "user", None)
    if usuario is not None and not usuario.is_authenticated:
        usuario = None

    return LogAuditoria.objects.create(
        tenant=tenant,
        usuario=usuario,
        modelo=instancia.__class__.__name__,
        objeto_id=str(instancia.pk),
        acao=acao,
        alteracoes=diferenca(antes or {}, depois or {}) if (antes or depois) else {},
        ip=ip_do_request(request) if request else None,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
    )
