#!/usr/bin/env bash
# Roda as 3 evals de uma competência e reporta o exit code de cada uma.
# Existe porque o bridge Windows->WSL engole $? — e uma eval cujo código de
# saída ninguém consegue ler não é gate, é impressão de texto.
set -uo pipefail
cd "$(dirname "$0")/.."

comp="${1:?uso: rodar_evals.sh AAAA-MM}"
falhou=0

for e in eval_packets eval_coerencia eval_doutrina; do
  echo "─────────── $e · $comp ───────────"
  .venv/bin/python "scripts/$e.py" --competencia "$comp"
  rc=$?
  echo "  [exit $rc]"
  [ $rc -ne 0 ] && falhou=1
done

echo ""
if [ $falhou -eq 0 ]; then
  echo "TODAS AS EVALS PASSARAM · $comp"
else
  echo "HOUVE EVAL REPROVADA · $comp"
fi
exit $falhou
