#!/usr/bin/env bash
# scaffold.sh — gera o par (architect + developer) de uma tech do menu.
#
#   bash .claude/skills/novo-agente/scaffold.sh <slug>
#   bash .claude/skills/novo-agente/scaffold.sh --refresh    # regenera todos
#
# Arquivo gerado NÃO se edita à mão: mude menu/techs.yaml ou o template e
# regenere, senão o --refresh sobrescreve sua edição sem avisar.
#
# Exit: 0 ok · 1 erro de uso · 2 tech ausente do menu

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SKILL_DIR}/../../.." && pwd)"
MENU="${SKILL_DIR}/menu/techs.yaml"
AGENTS="${REPO}/.claude/agents"
PY="${REPO}/.venv/bin/python"
[[ -x "${PY}" ]] || PY="python3"

render() {
  local slug="$1"
  "${PY}" - "$slug" "$MENU" "$SKILL_DIR" "$AGENTS" <<'PYEOF'
import sys, datetime, pathlib
try:
    import yaml
except ImportError:
    sys.exit("faltou pyyaml: .venv/bin/pip install pyyaml")

slug, menu_path, skill_dir, agents_dir = sys.argv[1:5]
menu = yaml.safe_load(pathlib.Path(menu_path).read_text(encoding="utf-8")) or {}
tech = menu.get(slug)
if not tech:
    disponiveis = [k for k in menu if k != "schema_version"]
    sys.exit(f"'{slug}' não está no menu. Disponíveis: {', '.join(disponiveis)}")

faltando = [c for c in ("display_name", "description", "threshold_architect",
                        "threshold_developer", "maxim", "mission_architect",
                        "mission_developer") if c not in tech]
if faltando:
    sys.exit(f"entrada '{slug}' incompleta: falta {', '.join(faltando)}")

def bloco(itens):
    if not itens:
        return "_(nenhuma declarada — preencha em menu/techs.yaml)_"
    return "\n".join(f"- {i}" for i in itens)

comum = {
    "SLUG": slug,
    "DISPLAY_NAME": tech["display_name"],
    "DESCRIPTION": tech["description"],
    "THRESHOLD_ARCHITECT": str(tech["threshold_architect"]),
    "THRESHOLD_DEVELOPER": str(tech["threshold_developer"]),
    "COLOR_ARCHITECT": tech.get("color_architect", "blue"),
    "COLOR_DEVELOPER": tech.get("color_developer", "blue"),
    "MAXIM": tech["maxim"],
    "MISSION_ARCHITECT": tech["mission_architect"],
    "MISSION_DEVELOPER": tech["mission_developer"],
    "CAPABILITIES_ARCHITECT": bloco(tech.get("capabilities_architect")),
    "CAPABILITIES_DEVELOPER": bloco(tech.get("capabilities_developer")),
    "GERADO_EM": datetime.date.today().isoformat(),
}

for papel in ("architect", "developer"):
    tpl = pathlib.Path(skill_dir, "templates", f"{papel}.md.tpl").read_text(encoding="utf-8")
    for k, v in comum.items():
        tpl = tpl.replace("{" + k + "}", v)
    destino = pathlib.Path(agents_dir, f"{slug}-{papel}.md")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(tpl, encoding="utf-8")
    print(f"  gerado: .claude/agents/{destino.name}")
PYEOF
}

if [[ "${1:-}" == "--refresh" ]]; then
  echo "regenerando todos os agentes do menu…"
  for f in "${AGENTS}"/*-architect.md; do
    [[ -e "$f" ]] || continue
    slug="$(basename "$f" -architect.md)"
    render "$slug" || echo "  (pulado: $slug não está mais no menu)"
  done
  echo "pronto. verifique: bash ${SKILL_DIR}/quality-gate.sh --strict"
  exit 0
fi

if [[ -z "${1:-}" ]]; then
  echo "uso: scaffold.sh <slug> | --refresh" >&2
  echo "" >&2
  echo "no menu:" >&2
  grep -E "^[a-z][a-z0-9_-]*:" "$MENU" | tr -d ':' | sed 's/^/  /' >&2
  exit 1
fi

render "$1"
echo ""
echo "verifique antes de usar:"
echo "  bash ${SKILL_DIR}/quality-gate.sh --strict"
