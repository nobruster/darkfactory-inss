#!/usr/bin/env bash
# Confere retroativamente cada Bronze publicado contra a âncora medida.
set -uo pipefail
cd "$(dirname "$0")/.."
falhou=0
for comp in "$@"; do
  echo "=============== $comp ==============="
  .venv/bin/python scripts/ancorar_bronze.py --competencia "$comp" || falhou=1
done
exit $falhou
