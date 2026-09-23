#!/usr/bin/env bash
# Roda a análise de qualidade completa: lint, testes com cobertura nos dois
# projetos e o scanner do SonarQube.
#
#   ./scripts/qualidade.sh            # análise completa
#   ./scripts/qualidade.sh --so-scan  # só o scanner (reaproveita a cobertura)
#
# Pré-requisitos:
#   docker compose -f docker-compose.qualidade.yml up -d sonarqube
#   export SONAR_TOKEN=<token de análise gerado no SonarQube>
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

SONAR_URL="${SONAR_URL:-http://localhost:9000}"
SONAR_REDE="${SONAR_REDE:-imobipro-qualidade_default}"

if [[ "${1:-}" != "--so-scan" ]]; then
  echo "==> Backend: lint, formatação e testes com cobertura"
  docker compose run --rm \
    -e DJANGO_SETTINGS_MODULE=config.settings.test \
    -e DATABASE_URL=postgres://imobipro:imobipro@db:5432/imobipro_test \
    api sh -c "ruff check . && black --check apps config -q && pytest -q --cov-report=xml"

  echo "==> Frontend: lint, testes com cobertura e build"
  (cd imobipro-web && npm run lint && npx vitest run --coverage && npm run build)
fi

echo "==> Ajustando caminhos dos relatórios de cobertura"
# O coverage.xml é escrito pelo usuário do contêiner, então o ajuste roda lá.
docker compose run --rm api python scripts_ajuste.py 2>/dev/null ||
  docker compose run --rm -v "$RAIZ/scripts:/scripts" api \
    python /scripts/ajustar_cobertura.py --python /app/coverage.xml --javascript ""
python3 scripts/ajustar_cobertura.py --python ""

echo "==> Scanner SonarQube"
: "${SONAR_TOKEN:?defina SONAR_TOKEN com um token de análise do SonarQube}"
docker run --rm --network "$SONAR_REDE" \
  -e SONAR_HOST_URL=http://sonarqube:9000 \
  -e SONAR_TOKEN="$SONAR_TOKEN" \
  -v "$RAIZ:/usr/src" \
  sonarsource/sonar-scanner-cli:latest | tail -5

echo "==> Resultado em $SONAR_URL/dashboard?id=imobipro"
