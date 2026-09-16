#!/usr/bin/env bash
# Roda as 3 evals de cada competência com lakehouse construído.
set -uo pipefail
cd "$(dirname "$0")/.."
falhou=0
for comp in "$@"; do
  echo ""
  echo "###################### $comp ######################"
  bash scripts/rodar_evals.sh "$comp" || falhou=1
done
echo ""
[ $falhou -eq 0 ] && echo "TUDO VERDE em: $*" || echo "HOUVE REPROVAÇÃO"
exit $falhou
