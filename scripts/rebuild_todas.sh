#!/usr/bin/env bash
# Reconstrói Silver e Gold de todas as competências com lakehouse presente.
# Bronze não é refeito: o Parquet e seu sha256 já estão publicados e a
# reconstrução parte dele, como manda a doutrina (cada camada reconstrói só
# a partir da anterior).
set -uo pipefail
cd "$(dirname "$0")/.."

PY=.venv/bin/python
falhou=0

for comp in "$@"; do
  echo "=============== $comp ==============="
  if ! $PY scripts/build_silver.py --competencia "$comp"; then
    echo "  SILVER reprovou em $comp"; falhou=1; continue
  fi
  if ! $PY scripts/build_gold.py --competencia "$comp"; then
    echo "  GOLD reprovou em $comp"; falhou=1
  fi
done

exit $falhou
