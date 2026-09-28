"""Geração de PDF a partir de template Django (WeasyPrint)."""

from django.http import HttpResponse
from django.template.loader import render_to_string


def renderizar_pdf(template: str, contexto: dict, base_url=None) -> bytes:
    from weasyprint import HTML

    html = render_to_string(template, contexto)
    return HTML(string=html, base_url=base_url).write_pdf()


def resposta_pdf(template: str, contexto: dict, nome_arquivo: str, base_url=None):
    """Devolve o PDF já como anexo, com nome legível para o usuário."""

    conteudo = renderizar_pdf(template, contexto, base_url=base_url)
    resposta = HttpResponse(conteudo, content_type="application/pdf")
    resposta["Content-Disposition"] = f'inline; filename="{nome_arquivo}"'
    return resposta
