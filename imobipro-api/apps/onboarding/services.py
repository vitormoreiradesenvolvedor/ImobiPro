"""Avaliação do progresso: missões conferidas contra o dado real."""

from django.utils import timezone

from apps.onboarding.missoes import TRILHAS, missoes_do_papel, nivel_para
from apps.onboarding.models import ProgressoOnboarding


def progresso_do_usuario(usuario) -> ProgressoOnboarding:
    progresso, _ = ProgressoOnboarding.objects.get_or_create(
        usuario=usuario, defaults={"tenant": usuario.tenant}
    )
    return progresso


def avaliar(usuario):
    """Estado completo do onboarding: missões, pontos, nível e trilhas."""

    progresso = progresso_do_usuario(usuario)
    tenant = usuario.tenant
    catalogo = missoes_do_papel(usuario.papel)

    missoes = []
    pontos = 0
    total_pontos = 0
    proxima = None

    for missao in catalogo:
        concluida = bool(tenant) and missao.verificar(tenant)
        total_pontos += missao.pontos
        if concluida:
            pontos += missao.pontos
        elif proxima is None:
            proxima = missao.chave

        missoes.append(
            {
                "chave": missao.chave,
                "titulo": missao.titulo,
                "descricao": missao.descricao,
                "dica": missao.dica,
                "trilha": missao.trilha,
                "trilha_nome": TRILHAS[missao.trilha]["nome"],
                "trilha_icone": TRILHAS[missao.trilha]["icone"],
                "rota": missao.rota,
                "pontos": missao.pontos,
                "concluida": concluida,
                "proxima": False,
            }
        )

    for item in missoes:
        item["proxima"] = item["chave"] == proxima

    concluidas = sum(1 for m in missoes if m["concluida"])
    tudo_pronto = concluidas == len(missoes) and missoes

    if tudo_pronto and progresso.concluido_em is None:
        progresso.concluido_em = timezone.now()
        progresso.save(update_fields=["concluido_em", "atualizado_em"])

    return {
        "missoes": missoes,
        "trilhas": _resumo_por_trilha(missoes),
        "concluidas": concluidas,
        "total": len(missoes),
        "pontos": pontos,
        "total_pontos": total_pontos,
        "percentual": round(pontos / total_pontos * 100) if total_pontos else 0,
        "nivel": nivel_para(pontos),
        "proxima_missao": proxima,
        "tours_concluidos": progresso.tours_concluidos,
        "dispensado": progresso.dispensado,
        "concluido": bool(tudo_pronto),
    }


def _resumo_por_trilha(missoes):
    resumo = {}
    for missao in missoes:
        trilha = resumo.setdefault(
            missao["trilha"],
            {
                "chave": missao["trilha"],
                "nome": missao["trilha_nome"],
                "icone": missao["trilha_icone"],
                "total": 0,
                "concluidas": 0,
            },
        )
        trilha["total"] += 1
        trilha["concluidas"] += int(missao["concluida"])

    return list(resumo.values())


def concluir_tour(usuario, identificador: str):
    return progresso_do_usuario(usuario).marcar_tour(identificador)


def definir_dispensa(usuario, dispensado: bool):
    progresso = progresso_do_usuario(usuario)
    progresso.dispensado = dispensado
    progresso.save(update_fields=["dispensado", "atualizado_em"])
    return progresso


def reiniciar(usuario):
    """Zera só o guia nenhum dado da operação é tocado."""

    progresso = progresso_do_usuario(usuario)
    progresso.tours_concluidos = []
    progresso.dispensado = False
    progresso.concluido_em = None
    progresso.save(
        update_fields=["tours_concluidos", "dispensado", "concluido_em", "atualizado_em"]
    )
    return progresso
