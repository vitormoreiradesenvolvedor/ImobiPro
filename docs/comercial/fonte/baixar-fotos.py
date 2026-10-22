"""Baixa as fotos de imóveis usadas na demonstração.

    python3 docs/comercial/fonte/baixar-fotos.py /caminho/de/saida

Busca no Openverse apenas imagens CC0 ou de domínio público, recorta em 3:2 e
grava a procedência em `creditos.json`. Fotografia real é o que faz a
demonstração parecer com o dia a dia de uma imobiliária.
"""

import json
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

CATEGORIAS = {
    "fachada": ["modern house exterior", "house facade modern", "apartment building exterior"],
    "sala": ["modern living room", "living room interior design", "minimalist living room"],
    "cozinha": ["modern kitchen interior", "kitchen interior design"],
    "quarto": ["modern bedroom interior", "bedroom interior design"],
    "banheiro": ["modern bathroom interior", "bathroom interior design"],
    "terreno": ["empty land lot", "vacant land plot", "green field land"],
    "comercial": ["modern office interior", "office building facade", "coworking office space"],
    "apartamento": ["apartment building modern", "apartment balcony view"],
}

# Ilustração e pintura não servem: a demonstração precisa parecer real.
DESCARTE = ("png", "psd", "illustration", "vintage", "painting", "drawing")


def buscar(consulta, quantidade=12):
    parametros = urllib.parse.urlencode(
        {
            "q": consulta,
            "license": "cc0,pdm",
            "page_size": quantidade,
            "source": "rawpixel",
            "size": "large",
            "mature": "false",
        }
    )
    requisicao = urllib.request.Request(
        f"https://api.openverse.org/v1/images/?{parametros}",
        headers={"User-Agent": "ImobiPro-demo/1.0"},
    )
    with urllib.request.urlopen(requisicao, timeout=30) as resposta:
        return json.load(resposta).get("results", [])


def principal(saida):
    bruto = saida / "bruto"
    prontas = saida / "prontas"
    bruto.mkdir(parents=True, exist_ok=True)
    prontas.mkdir(parents=True, exist_ok=True)

    creditos = []
    for categoria, consultas in CATEGORIAS.items():
        indice = 0
        for consulta in consultas:
            for item in buscar(consulta):
                url = item.get("url")
                titulo = (item.get("title") or "").lower()
                if not url or any(palavra in titulo for palavra in DESCARTE):
                    continue

                indice += 1
                arquivo = bruto / f"{categoria}-{indice:02d}.jpg"
                try:
                    requisicao = urllib.request.Request(
                        url, headers={"User-Agent": "ImobiPro-demo/1.0"}
                    )
                    with urllib.request.urlopen(requisicao, timeout=45) as resposta:
                        conteudo = resposta.read()
                    if len(conteudo) < 25_000:
                        indice -= 1
                        continue
                    arquivo.write_bytes(conteudo)
                    subprocess.run(
                        [
                            "magick", str(arquivo), "-auto-orient",
                            "-resize", "1600x1600^", "-gravity", "center",
                            "-crop", "1600x1067+0+0", "+repage",
                            "-quality", "82", str(prontas / arquivo.name),
                        ],
                        check=True,
                    )
                    creditos.append(
                        {
                            "arquivo": arquivo.name,
                            "categoria": categoria,
                            "titulo": item.get("title"),
                            "licenca": item.get("license"),
                            "fonte": item.get("foreign_landing_url"),
                            "autor": item.get("creator"),
                        }
                    )
                except Exception as erro:  # rede é instável: pula e segue
                    indice -= 1
                    print("falhou", url[:60], erro)

                if indice >= 10:
                    break
            if indice >= 10:
                break
        print(categoria, indice)

    (saida / "creditos.json").write_text(
        json.dumps(creditos, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("total:", len(creditos))


if __name__ == "__main__":
    principal(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "fotos"))
