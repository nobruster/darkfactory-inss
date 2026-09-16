#!/usr/bin/env bash
# Reexecuta o Bronze das competências dadas, agora com a âncora ligada.
# Não é cosmético: os packets antigos dizem ACEITO com o gate de total
# desligado. Um packet só pode dizer que o gate passou se o gate rodou.
set -uo pipefail
cd "$(dirname "$0")/.."
falhou=0
for comp in "$@"; do
  echo "=============== BRONZE $comp ==============="
  .venv/bin/python ingestion/ingest_bronze.py --competencia "$comp" || falhou=1
done
exit $falhou
