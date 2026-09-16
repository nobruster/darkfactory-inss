#!/usr/bin/env bash
# quality-gate.sh — a skill nova-fabrica está íntegra?
#
# Um gerador quebrado produz fábricas quebradas em silêncio: o arquivo sai,
# tem o nome certo, e só o gate da fábrica gerada descobre — se descobrir.
#
#   bash .claude/skills/nova-fabrica/quality-gate.sh [--strict]
#
# Exit: 0 aprovado · 7 BLOCKER em --strict

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${DIR}/../../.." && pwd)"
PY="${REPO}/.venv/bin/python"
[[ -x "${PY}" ]] || PY="python3"
MENU="${DIR}/menu/fabricas.yaml"

STRICT=0
[[ "${1:-}" == "--strict" ]] && STRICT=1

BLOCKER=0
IMPORTANT=0

blocker()   { echo "  BLOCKER   $*";   BLOCKER=$((BLOCKER + 1)); }
important() { echo "  IMPORTANT $*"; IMPORTANT=$((IMPORTANT + 1)); }

echo "────────────────────────────────────────────────────────────"
echo "  gate da skill nova-fabrica"
echo "────────────────────────────────────────────────────────────"

# ── 1. arquivos que a skill precisa ter ──────────────────────────────
for f in SKILL.md scaffold.sh menu/fabricas.yaml; do
  [[ -f "${DIR}/${f}" ]] || blocker "falta ${f}"
done

# ── 2. todo template que o scaffold cita tem de existir ──────────────
# Sem isto, o scaffold avisa "template ausente" e segue: a fábrica nasce
# sem Makefile e ninguém repara até rodar `make`.
CITADOS=$("${PY}" - "${DIR}/scaffold.sh" <<'PYEOF'
import re
import sys

txt = open(sys.argv[1], encoding="utf-8").read()
# pega o dict MAPA_TPL e as chaves "algo.tpl"
bloco = re.search(r"MAPA_TPL\s*=\s*\{(.*?)\}", txt, re.S)
if bloco:
    for m in re.finditer(r'"([^"]+\.tpl)"', bloco.group(1)):
        print(m.group(1))
PYEOF
)
for tpl in ${CITADOS}; do
  [[ -f "${DIR}/templates/${tpl}" ]] || blocker "scaffold cita templates/${tpl}, que não existe"
done

# ── 3. os ADRs semente ───────────────────────────────────────────────
N_ADR=$(find "${DIR}/templates/adrs" -name '*.md.tpl' 2>/dev/null | wc -l)
[[ "${N_ADR}" -ge 3 ]] || important "só ${N_ADR} ADR(s) semente — esperado 3+"

# ── 4. o menu é YAML válido e as entradas estão completas ────────────
"${PY}" - "${DIR}/menu/fabricas.yaml" <<'PYEOF' || blocker "menu inválido"
import sys

import yaml

m = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
ruim = 0
for slug, f in m.items():
    # `_autoteste` é gerado pelo gate, então vale a mesma exigência.
    if slug == "schema_version" or (slug.startswith("_") and slug != "_autoteste"):
        continue
    fonte = f.get("fonte") or {}
    for campo, v in (("display_name", f.get("display_name")),
                     ("pergunta", f.get("pergunta")),
                     ("grao_gold", f.get("grao_gold")),
                     ("fonte.url_padrao", fonte.get("url_padrao")),
                     ("fonte.formato", fonte.get("formato"))):
        if not v:
            print(f"  entrada '{slug}' sem {campo}")
            ruim += 1
sys.exit(1 if ruim else 0)
PYEOF

# ── 5. sintaxe do shell e do Python ──────────────────────────────────
bash -n "${DIR}/scaffold.sh" 2>/dev/null || blocker "scaffold.sh não passa em bash -n"

for tpl in "${DIR}"/templates/*.py.tpl; do
  [[ -f "${tpl}" ]] || continue
  # o template tem {{VAR}}, que não é Python válido. Substituímos por um
  # literal antes de compilar — o que se testa é a ESTRUTURA do arquivo.
  "${PY}" - "${tpl}" <<'PYEOF' || blocker "$(basename "${tpl}") não compila"
import re
import sys

txt = open(sys.argv[1], encoding="utf-8").read()
txt = re.sub(r"\{\{[A-Z_]+\}\}", "X", txt)
compile(txt, sys.argv[1], "exec")
PYEOF
done

# ── 6. os templates YAML/JSON continuam válidos após substituição ────
"${PY}" - "${DIR}" <<'PYEOF' || blocker "template YAML/JSON inválido"
import json
import pathlib
import re
import sys

import yaml

d = pathlib.Path(sys.argv[1]) / "templates"
subs = {
    "SENTINELAS": "{}", "GRAO_SILVER": "[]", "GRAO_GOLD": '["a"]',
    "COLUNAS_MONETARIAS": "[]", "CHAVES_SUSPEITAS": "[]",
    "TEM_CABECALHO": "true",
}
ruim = 0
for p in sorted(d.glob("*.tpl")):
    if not p.name.endswith((".yaml.tpl", ".yml.tpl", ".json.tpl")):
        continue
    txt = p.read_text(encoding="utf-8")
    for k, v in subs.items():
        txt = txt.replace("{{" + k + "}}", v)
    txt = re.sub(r"\{\{[A-Z_]+\}\}", "x", txt)
    try:
        if p.name.endswith(".json.tpl"):
            json.loads(txt)
        else:
            yaml.safe_load(txt)
    except Exception as e:
        print(f"  {p.name}: {str(e)[:90]}")
        ruim += 1
sys.exit(1 if ruim else 0)
PYEOF

# ── 7. a skill não pode prometer no SKILL.md o que não gera ──────────
for alvo in "make ancora" "ACEITO_SEM_ANCORA" "NAO_MEDIDO"; do
  grep -qF "${alvo}" "${DIR}/SKILL.md" || important "SKILL.md não menciona ${alvo}"
done
grep -qF "NAO_MEDIDO" "${DIR}/templates/layout.yaml.tpl" 2>/dev/null \
  || blocker "o contrato gerado não nasce NAO_MEDIDO — a fábrica construiria sem juiz"

# ── 8. o teste que importa: gerar de verdade e conferir ──────────────
# Um gerador só se prova gerando. Os testes acima olham a skill; este
# olha o PRODUTO — que é onde o defeito aparece (Makefile citando script
# inexistente passou por todos os outros checks).
TMPH="$(mktemp -d)"
# Prefere `_autoteste` (existe para isto e não toca a rede); se alguém o
# tiver removido, cai na primeira entrada real do menu.
PRIMEIRO=$("${PY}" -c "
import yaml
m = yaml.safe_load(open('${MENU}', encoding='utf-8')) or {}
if '_autoteste' in m:
    print('_autoteste')
else:
    c = [k for k in m if not k.startswith('_') and k != 'schema_version']
    print(c[0] if c else '')
" 2>/dev/null)

if [[ -z "${PRIMEIRO}" ]]; then
  important "menu sem entrada gerável — não deu para provar o gerador"
else
  if HOME="${TMPH}" bash "${DIR}/scaffold.sh" "${PRIMEIRO}" >/dev/null 2>&1; then
    if ! "${PY}" "${DIR}/verificar_fabrica.py" \
         "${TMPH}/darkfactory-${PRIMEIRO}" 2>&1 | grep -q "^  OK"; then
      blocker "a fábrica gerada de '${PRIMEIRO}' não passa em verificar_fabrica.py"
      "${PY}" "${DIR}/verificar_fabrica.py" "${TMPH}/darkfactory-${PRIMEIRO}" 2>&1 \
        | sed -n '2,12p' | sed 's/^/    /'
    fi
  else
    blocker "scaffold.sh falhou ao gerar '${PRIMEIRO}'"
  fi
fi
rm -rf "${TMPH}"

echo "────────────────────────────────────────────────────────────"
echo "  BLOCKER   : ${BLOCKER}"
echo "  IMPORTANT : ${IMPORTANT}"
echo ""
if [[ ${BLOCKER} -gt 0 ]]; then
  echo "  VEREDITO: REPROVA"
  [[ ${STRICT} -eq 1 ]] && exit 7
  exit 0
fi
echo "  VEREDITO: APROVA"
exit 0
