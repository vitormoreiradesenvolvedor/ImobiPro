"""Processamento assíncrono de mídia do imóvel."""

import logging
from io import BytesIO

from celery import shared_task
from django.core.files.base import ContentFile
from PIL import Image

logger = logging.getLogger(__name__)

TAMANHO_THUMB = (600, 400)
QUALIDADE = 82


@shared_task(name="imoveis.gerar_thumbnail")
def gerar_thumbnail(foto_id):
    """Gera a miniatura em WebP usada no grid e no mapa.

    Roda fora do request: subir 20 fotos não pode travar a tela de captação.
    """

    from apps.imoveis.models import FotoImovel

    try:
        foto = FotoImovel.objects.get(pk=foto_id)
    except FotoImovel.DoesNotExist:
        logger.warning("Foto %s não existe mais; thumbnail ignorado.", foto_id)
        return None

    with Image.open(foto.arquivo) as imagem:
        imagem = imagem.convert("RGB")
        imagem.thumbnail(TAMANHO_THUMB)

        buffer = BytesIO()
        imagem.save(buffer, format="WEBP", quality=QUALIDADE)

    nome = f"{foto.pk}.webp"
    foto.arquivo_thumb.save(nome, ContentFile(buffer.getvalue()), save=True)
    return foto.arquivo_thumb.name


@shared_task(name="imoveis.alertar_exclusividade_a_vencer")
def alertar_exclusividade_a_vencer(dias=15):
    """Avisa o captador que a exclusividade está acabando (handoff §1.3)."""

    from apps.accounts.models import Tenant
    from apps.imoveis.services import exclusividades_a_vencer
    from apps.notificacoes.services import notificar_usuario

    total = 0
    for tenant in Tenant.objects.filter(ativo=True):
        for imovel in exclusividades_a_vencer(tenant, dias).select_related("captador"):
            if not imovel.captador_id:
                continue
            notificar_usuario(
                imovel.captador,
                tipo="EXCLUSIVIDADE_A_VENCER",
                titulo=f"Exclusividade do {imovel.codigo} vence em breve",
                descricao=f"{imovel.titulo} até {imovel.exclusividade_ate:%d/%m/%Y}.",
                dados={"imovel_id": str(imovel.pk)},
            )
            total += 1

    return total
