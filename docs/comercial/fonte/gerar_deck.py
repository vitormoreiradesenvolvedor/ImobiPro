"""Monta o deck comercial: um arquivo, tudo embutido, navegável pelo teclado."""

import base64
import html
import pathlib
import sys

BASE = pathlib.Path(__file__).parent
sys.path.insert(0, str(BASE))
from fontes import FONTES  # noqa: E402
from slides import SLIDES  # noqa: E402

TELAS = BASE / "slides"


def esc(t):
    return html.escape(str(t))


def imagem(nome):
    dados = (TELAS / f"{nome}.jpg").read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(dados).decode()


def face(familia, peso, chave):
    return (
        "@font-face{font-family:'%s';font-weight:%s;font-style:normal;font-display:block;"
        "src:url(data:font/otf;base64,%s) format('opentype')}" % (familia, peso, FONTES[chave])
    )


fontes = "".join(
    [
        face("Deck Display", "800", "display"),
        face("Deck Texto", "400", "corpo"),
        face("Deck Texto", "700", "corpo_bold"),
    ]
)


def montar(slide, numero):
    tipo = slide["tipo"]
    eyebrow = f'<p class="eyebrow">{esc(slide.get("eyebrow", ""))}</p>' if slide.get("eyebrow") else ""
    corpo = ""
    classe = f"slide slide--{tipo}"

    if tipo == "capa":
        corpo = f"""
        <div class="capa">
          <span class="marca">iP</span>
          {eyebrow}
          <h1>{esc(slide['titulo'])}</h1>
          <p class="capa__linha">{esc(slide['linha'])}</p>
          <p class="capa__rodape">{esc(slide['rodape'])}</p>
        </div>"""

    elif tipo == "perguntas":
        itens = "".join(
            f"""<li>
              <p class="pergunta">{esc(p)}</p>
              <p class="pergunta__nota">{esc(n)}</p>
            </li>"""
            for p, n in slide["itens"]
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2><ol class="perguntas">{itens}</ol>"""

    elif tipo == "problema":
        colunas = "".join(
            f"""<article class="cartao">
              <h3>{esc(t)}</h3>
              <p>{esc(d)}</p>
            </article>"""
            for t, d in slide["colunas"]
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2><div class="trio">{colunas}</div>"""

    elif tipo == "conta":
        linhas = "".join(
            f"<tr><th>{esc(r)}</th><td>{esc(v)}</td></tr>" for r, v in slide["exemplo"]
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2>
        <div class="conta">
          <table><caption>Exemplo. Troque pelos números do lead</caption><tbody>{linhas}</tbody></table>
          <p class="conta__fecho">{esc(slide['fecho'])}</p>
        </div>"""

    elif tipo == "ciclo":
        etapas = "".join(
            f"""<li><span class="ciclo__num">{indice:02d}</span>
              <p class="ciclo__nome">{esc(nome)}</p>
              <p class="ciclo__desc">{esc(desc)}</p></li>"""
            for indice, (nome, desc) in enumerate(slide["etapas"], start=1)
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2><ol class="ciclo">{etapas}</ol>"""

    elif tipo == "tela":
        itens = "".join(f"<li>{esc(i)}</li>" for i in slide["itens"])
        corpo = f"""<div class="tela">
          <div class="tela__texto">{eyebrow}<h2>{esc(slide['titulo'])}</h2><ul>{itens}</ul></div>
          <figure class="tela__imagem"><img src="{imagem(slide['imagem'])}" alt="{esc(slide['titulo'])}" /></figure>
        </div>"""

    elif tipo == "numeros":
        metricas = "".join(
            f"""<div class="metrica"><p class="metrica__valor">{esc(v)}</p>
              <p class="metrica__rotulo">{esc(r)}</p>
              <p class="metrica__nota">{esc(n)}</p></div>"""
            for v, r, n in slide["metricas"]
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2><div class="metricas">{metricas}</div>"""

    elif tipo == "etapas":
        etapas = "".join(
            f"""<li><p class="etapa__quando">{esc(q)}</p>
              <p class="etapa__nome">{esc(n)}</p>
              <p class="etapa__desc">{esc(d)}</p></li>"""
            for q, n, d in slide["etapas"]
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2><ol class="etapas">{etapas}</ol>"""

    elif tipo == "colunas":
        colunas = "".join(
            f"""<article class="cartao"><h3>{esc(t)}</h3><p>{esc(d)}</p></article>"""
            for t, d in slide["colunas"]
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2><div class="trio">{colunas}</div>
        <p class="aviso">{esc(slide['aviso'])}</p>"""

    elif tipo == "objecoes":
        pares = "".join(
            f"""<li><p class="objecao">{esc(o)}</p><p class="resposta">{esc(r)}</p></li>"""
            for o, r in slide["pares"]
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2><ul class="objecoes">{pares}</ul>"""

    elif tipo == "roteiro":
        passos = "".join(
            f"""<li><span class="roteiro__tempo">{esc(t)}</span>
              <span class="roteiro__tela">{esc(n)}</span>
              <span class="roteiro__acao">{esc(a)}</span></li>"""
            for t, n, a in slide["passos"]
        )
        corpo = f"""{eyebrow}<h2>{esc(slide['titulo'])}</h2><ol class="roteiro">{passos}</ol>"""

    elif tipo == "fecho":
        itens = "".join(f"<li>{esc(i)}</li>" for i in slide["itens"])
        corpo = f"""<div class="capa">
          {eyebrow}
          <h1>{esc(slide['titulo'])}</h1>
          <p class="capa__linha">{esc(slide['linha'])}</p>
          <ul class="fecho">{itens}</ul>
          <p class="capa__rodape">{esc(slide['rodape'])}</p>
        </div>"""

    notas = f'<aside class="notas"><b>Nota do apresentador</b> {esc(slide["notas"])}</aside>'
    return f"""<section class="{classe}" id="s{numero}" data-numero="{numero}">
      <div class="quadro">{corpo}</div>
      {notas}
      <p class="paginacao">{numero} / {len(SLIDES)}</p>
    </section>"""


slides_html = "".join(montar(slide, indice) for indice, slide in enumerate(SLIDES, start=1))

# O charset precisa vir declarado: aberto por file://, o navegador assume
# Windows-1252 e todo acento vira mojibake no PDF.
pagina = f"""<meta charset="utf-8">
<title>ImobiPro apresentação comercial</title>
<style>
{fontes}

:root {{
  --fundo: #061a16;
  --fundo-claro: #f3f7f4;
  --tinta: #f0f6f2;
  --tinta-escura: #0a1f1b;
  --tinta-fraca: #9fbcb2;
  --tinta-fraca-clara: #5c7a71;
  --marca: #23c4a5;
  --marca-escura: #0c6d5c;
  --destaque: #e8a33d;
  --traco: rgba(255,255,255,.14);
  --traco-claro: #d4e0d8;
}}

* {{ box-sizing: border-box; }}

body {{
  margin: 0;
  background: #030d0b;
  color: var(--tinta);
  font-family: 'Deck Texto', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
}}

h1, h2, h3 {{
  font-family: 'Deck Display', system-ui, sans-serif;
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: -.025em;
  text-wrap: balance;
  margin: 0;
}}

/* ------------------------------------------------------------------ palco */

#palco {{
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}}

.slide {{
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: clamp(2rem, 4vw, 4.5rem);
  background: var(--fundo);
  opacity: 0;
  visibility: hidden;
  transition: opacity .32s ease;
}}
.slide.ativo {{ opacity: 1; visibility: visible; }}

.quadro {{ width: min(100%, 78rem); }}

.slide--tela, .slide--numeros, .slide--roteiro, .slide--objecoes, .slide--etapas {{
  background: var(--fundo-claro);
  color: var(--tinta-escura);
}}

.eyebrow {{
  margin: 0 0 1rem;
  font-size: clamp(.7rem, 1vw, .82rem);
  letter-spacing: .3em;
  text-transform: uppercase;
  color: var(--marca);
  font-weight: 700;
}}
.slide--tela .eyebrow, .slide--numeros .eyebrow, .slide--roteiro .eyebrow,
.slide--objecoes .eyebrow, .slide--etapas .eyebrow {{ color: var(--marca-escura); }}

h2 {{ font-size: clamp(1.9rem, 3.6vw, 3.1rem); max-width: 22ch; }}

/* ------------------------------------------------------------------- capa */

.capa {{ text-align: center; display: grid; justify-items: center; gap: .4rem; }}
.capa .marca {{
  display: grid; place-items: center; width: 92px; height: 92px;
  border-radius: 24px; background: var(--marca); color: #04201b;
  font-family: 'Deck Display', system-ui, sans-serif; font-size: 2.6rem; margin-bottom: 1.6rem;
}}
.capa h1 {{ font-size: clamp(3rem, 8vw, 6rem); }}
.capa__linha {{
  margin: 1.2rem 0 0; font-size: clamp(1.15rem, 2.2vw, 1.7rem);
  color: var(--tinta-fraca); max-width: 34ch;
}}
.capa__rodape {{
  margin: 2.6rem 0 0; font-size: .95rem; color: var(--tinta-fraca);
  border-top: 1px solid var(--traco); padding-top: 1.2rem; max-width: 46ch;
}}
.fecho {{
  margin: 2rem 0 0; padding: 0; list-style: none; display: grid; gap: .7rem;
  font-size: 1.1rem; color: var(--tinta); text-align: left; justify-items: start;
}}
.fecho li {{ display: flex; gap: .8rem; align-items: baseline; }}
.fecho li::before {{ content: '→'; color: var(--marca); }}

/* -------------------------------------------------------------- perguntas */

.perguntas {{ margin: 2.4rem 0 0; padding: 0; list-style: none; display: grid; gap: 1.4rem; counter-reset: p; }}
.perguntas li {{
  border-left: 3px solid var(--marca); padding-left: 1.4rem; counter-increment: p;
}}
.pergunta {{ margin: 0; font-size: clamp(1.15rem, 2vw, 1.55rem); font-weight: 700; }}
.pergunta::before {{ content: counter(p) '. '; color: var(--marca); }}
.pergunta__nota {{ margin: .35rem 0 0; color: var(--tinta-fraca); max-width: 70ch; }}

/* ------------------------------------------------------------------- trio */

.trio {{ margin-top: 2.4rem; display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.4rem; }}
.cartao {{
  background: rgba(255,255,255,.05); border: 1px solid var(--traco);
  border-radius: 10px; padding: 1.6rem 1.5rem;
}}
.slide--colunas .cartao {{ border-top: 3px solid var(--marca); }}
.cartao h3 {{ font-size: 1.35rem; margin-bottom: .7rem; }}
.cartao p {{ margin: 0; color: var(--tinta-fraca); line-height: 1.6; }}
.aviso {{
  margin: 1.8rem 0 0; padding: .9rem 1.2rem; border-radius: 8px;
  background: rgba(232,163,61,.12); border: 1px solid rgba(232,163,61,.4);
  color: var(--destaque); font-size: .98rem;
}}

/* ------------------------------------------------------------------ conta */

.conta {{ margin-top: 2rem; display: grid; grid-template-columns: 1.1fr 1fr; gap: 2.5rem; align-items: start; }}
.conta table {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }}
.conta caption {{
  text-align: left; color: var(--destaque); font-size: .8rem; letter-spacing: .12em;
  text-transform: uppercase; padding-bottom: .8rem;
}}
.conta th {{
  text-align: left; font-weight: 400; color: var(--tinta-fraca);
  padding: .7rem 0; border-bottom: 1px solid var(--traco);
}}
.conta td {{
  text-align: right; font-weight: 700; padding: .7rem 0;
  border-bottom: 1px solid var(--traco);
}}
.conta tr:nth-child(4) td, .conta tr:nth-child(5) td {{ color: var(--marca); }}
.conta__fecho {{ margin: 0; font-size: 1.15rem; line-height: 1.65; color: var(--tinta); }}

/* ------------------------------------------------------------------ ciclo */

.ciclo {{ margin: 2.4rem 0 0; padding: 0; list-style: none; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }}
.ciclo li {{ background: rgba(255,255,255,.05); border-radius: 10px; padding: 1.2rem 1.1rem; border: 1px solid var(--traco); }}
.ciclo__num {{ font-size: .78rem; color: var(--marca); font-weight: 700; letter-spacing: .1em; }}
.ciclo__nome {{ margin: .4rem 0 .2rem; font-weight: 700; font-size: 1.15rem; }}
.ciclo__desc {{ margin: 0; font-size: .92rem; color: var(--tinta-fraca); line-height: 1.5; }}

/* ------------------------------------------------------------------- tela */

.tela {{ display: grid; grid-template-columns: 0.85fr 1.15fr; gap: 3rem; align-items: center; }}
.tela__texto ul {{ margin: 1.6rem 0 0; padding: 0; list-style: none; display: grid; gap: .9rem; }}
.tela__texto li {{
  padding-left: 1.5rem; position: relative; line-height: 1.6;
  color: var(--tinta-fraca-clara); font-size: 1.05rem;
}}
.tela__texto li::before {{
  content: ''; position: absolute; left: 0; top: .62em; width: 8px; height: 8px;
  border-radius: 50%; background: var(--marca-escura);
}}
.tela__imagem {{ margin: 0; }}
.tela__imagem img {{
  width: 100%; max-height: 68vh; object-fit: cover; object-position: top;
  border-radius: 10px; display: block;
  border: 1px solid var(--traco-claro);
  box-shadow: 0 24px 60px rgba(6,26,22,.22);
}}

/* ---------------------------------------------------------------- números */

.metricas {{ margin-top: 2.4rem; display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--traco-claro); border: 1px solid var(--traco-claro); border-radius: 10px; overflow: hidden; }}
.metrica {{ background: var(--fundo-claro); padding: 1.6rem 1.4rem; }}
.metrica__valor {{
  margin: 0; font-family: 'Deck Display', system-ui, sans-serif; font-size: 3rem;
  line-height: 1; color: var(--marca-escura); font-variant-numeric: tabular-nums;
}}
.metrica__rotulo {{ margin: .6rem 0 0; font-weight: 700; }}
.metrica__nota {{ margin: .1rem 0 0; color: var(--tinta-fraca-clara); font-size: .92rem; }}

/* ----------------------------------------------------------------- etapas */

.etapas {{ margin: 2.4rem 0 0; padding: 0; list-style: none; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.2rem; }}
.etapas li {{ border-top: 3px solid var(--marca-escura); padding-top: 1rem; }}
.etapa__quando {{ margin: 0; font-size: .8rem; letter-spacing: .1em; text-transform: uppercase; color: var(--marca-escura); font-weight: 700; }}
.etapa__nome {{ margin: .5rem 0 .3rem; font-weight: 700; font-size: 1.25rem; }}
.etapa__desc {{ margin: 0; color: var(--tinta-fraca-clara); line-height: 1.55; }}

/* --------------------------------------------------------------- objeções */

.objecoes {{ margin: 2rem 0 0; padding: 0; list-style: none; display: grid; gap: 1rem; }}
.objecoes li {{ display: grid; grid-template-columns: 1fr 1.6fr; gap: 1.6rem; align-items: start; padding-bottom: 1rem; border-bottom: 1px solid var(--traco-claro); }}
.objecao {{ margin: 0; font-weight: 700; font-size: 1.1rem; }}
.resposta {{ margin: 0; color: var(--tinta-fraca-clara); line-height: 1.6; }}

/* ---------------------------------------------------------------- roteiro */

.roteiro {{ margin: 2rem 0 0; padding: 0; list-style: none; display: grid; gap: .7rem; }}
.roteiro li {{ display: grid; grid-template-columns: 8rem 9rem 1fr; gap: 1.2rem; align-items: baseline; padding: .7rem 0; border-bottom: 1px solid var(--traco-claro); }}
.roteiro__tempo {{ font-variant-numeric: tabular-nums; color: var(--marca-escura); font-weight: 700; }}
.roteiro__tela {{ font-weight: 700; }}
.roteiro__acao {{ color: var(--tinta-fraca-clara); line-height: 1.55; }}

/* ------------------------------------------------------- notas e navegação */

.notas {{
  position: absolute; left: 0; right: 0; bottom: 0; display: none;
  padding: 1.1rem clamp(2rem, 4vw, 4.5rem); background: rgba(3,13,11,.96);
  color: #cfe3db; font-size: .95rem; line-height: 1.55;
  border-top: 2px solid var(--marca);
}}
.notas b {{ color: var(--marca); letter-spacing: .04em; }}
body.com-notas .notas {{ display: block; }}

.paginacao {{
  position: absolute; right: clamp(1.4rem, 3vw, 3rem); bottom: clamp(1rem, 2.4vw, 2rem);
  margin: 0; font-size: .85rem; color: var(--tinta-fraca); font-variant-numeric: tabular-nums;
}}
.slide--tela .paginacao, .slide--numeros .paginacao, .slide--roteiro .paginacao,
.slide--objecoes .paginacao, .slide--etapas .paginacao {{ color: var(--tinta-fraca-clara); }}

#progresso {{
  position: fixed; top: 0; left: 0; height: 3px; background: var(--marca);
  z-index: 10; transition: width .3s ease;
}}

#ajuda {{
  position: fixed; left: clamp(1.4rem, 3vw, 3rem); bottom: clamp(1rem, 2.4vw, 2rem);
  z-index: 10; margin: 0; font-size: .8rem; color: var(--tinta-fraca);
  opacity: .75;
}}
/* Em slide de fundo claro, a ajuda precisa de tinta escura para ser legível. */
body.slide-claro #ajuda {{ color: var(--tinta-fraca-clara); }}

kbd {{
  font-family: ui-monospace, monospace; font-size: .78rem; padding: .1rem .35rem;
  border: 1px solid currentColor; border-radius: 4px; opacity: .8;
}}

@media (max-width: 60rem) {{
  .trio, .metricas, .etapas {{ grid-template-columns: 1fr; }}
  .ciclo {{ grid-template-columns: repeat(2, 1fr); }}
  .tela, .conta {{ grid-template-columns: 1fr; gap: 1.4rem; }}
  .objecoes li, .roteiro li {{ grid-template-columns: 1fr; gap: .3rem; }}
}}

@media print {{
  body {{ overflow: visible; background: #fff; }}
  #palco {{ height: auto; }}
  .slide {{
    position: relative; opacity: 1; visibility: visible; page-break-after: always;
    height: 100vh; break-inside: avoid;
  }}
  #ajuda, #progresso {{ display: none; }}
  .notas {{ display: block; position: static; background: #f0f4f1; color: #24352f; }}
}}
</style>

<div id="progresso"></div>
<div id="palco">{slides_html}</div>
<p id="ajuda"><kbd>←</kbd> <kbd>→</kbd> navegar · <kbd>N</kbd> notas · <kbd>F</kbd> tela cheia · <kbd>P</kbd> imprimir</p>

<script>
  const slides = [...document.querySelectorAll('.slide')]
  const progresso = document.getElementById('progresso')
  let atual = 0

  const CLAROS = ['tela', 'numeros', 'roteiro', 'objecoes', 'etapas']

  function mostrar(indice) {{
    atual = Math.max(0, Math.min(slides.length - 1, indice))
    slides.forEach((s, i) => s.classList.toggle('ativo', i === atual))
    const tipo = [...slides[atual].classList]
      .find((c) => c.startsWith('slide--'))
      ?.replace('slide--', '')
    document.body.classList.toggle('slide-claro', CLAROS.includes(tipo))
    progresso.style.width = ((atual + 1) / slides.length * 100) + '%'
    history.replaceState(null, '', '#s' + (atual + 1))
  }}

  document.addEventListener('keydown', (evento) => {{
    const tecla = evento.key.toLowerCase()
    if (['arrowright', ' ', 'pagedown'].includes(tecla)) {{ evento.preventDefault(); mostrar(atual + 1) }}
    else if (['arrowleft', 'pageup'].includes(tecla)) {{ evento.preventDefault(); mostrar(atual - 1) }}
    else if (tecla === 'home') mostrar(0)
    else if (tecla === 'end') mostrar(slides.length - 1)
    else if (tecla === 'n') document.body.classList.toggle('com-notas')
    else if (tecla === 'f') {{
      if (document.fullscreenElement) document.exitFullscreen()
      else document.documentElement.requestFullscreen()
    }} else if (tecla === 'p') {{ evento.preventDefault(); window.print() }}
  }})

  document.getElementById('palco').addEventListener('click', (evento) => {{
    mostrar(evento.clientX < window.innerWidth * 0.25 ? atual - 1 : atual + 1)
  }})

  // Link direto para um slide funciona e continua funcionando ao trocar o hash.
  function daUrl() {{
    const numero = Number((location.hash || '#s1').replace('#s', ''))
    mostrar(Number.isFinite(numero) ? numero - 1 : 0)
  }}
  window.addEventListener('hashchange', daUrl)
  daUrl()
</script>
"""

destino = BASE / "deck-comercial.html"
destino.write_text(pagina, encoding="utf-8")
print(destino, f"{destino.stat().st_size / 1_000_000:.1f} MB", f"{len(SLIDES)} slides")
