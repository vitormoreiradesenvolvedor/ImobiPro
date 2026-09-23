"""Prefixa os caminhos dos relatórios de cobertura com o diretório do projeto.

O SonarQube analisa a raiz do repositório, mas cada suíte gera o relatório com
caminhos relativos à própria raiz (`apps/...`, `src/...`). Sem o prefixo, o
Sonar não casa a cobertura com os arquivos e mostra 0%.

Uso:
    python3 scripts/ajustar_cobertura.py            # ajusta o lcov do front
    python3 scripts/ajustar_cobertura.py --python /app/coverage.xml
"""

import argparse
import pathlib
import re


def ajustar_python(caminho: pathlib.Path) -> bool:
    if not caminho.exists():
        return False

    conteudo = caminho.read_text()
    conteudo = re.sub(
        r'filename="(?!imobipro-api/)', 'filename="imobipro-api/apps/', conteudo
    )
    conteudo = re.sub(r"<source>.*?</source>", "<source>.</source>", conteudo, flags=re.S)
    caminho.write_text(conteudo)
    return True


def ajustar_javascript(caminho: pathlib.Path) -> bool:
    if not caminho.exists():
        return False

    conteudo = caminho.read_text()
    conteudo = re.sub(r"^SF:(?!imobipro-web/)", "SF:imobipro-web/", conteudo, flags=re.M)
    caminho.write_text(conteudo)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", help="caminho do coverage.xml a ajustar")
    parser.add_argument(
        "--javascript",
        default="imobipro-web/coverage/lcov.info",
        help="caminho do lcov.info a ajustar",
    )
    argumentos = parser.parse_args()

    if argumentos.python and ajustar_python(pathlib.Path(argumentos.python)):
        print("  cobertura Python ajustada")

    if argumentos.javascript and ajustar_javascript(pathlib.Path(argumentos.javascript)):
        print("  cobertura JavaScript ajustada")


if __name__ == "__main__":
    main()
