#!/usr/bin/env bash
# quality-gate.sh — verifica que os agentes gerados prestam.
#
#   bash .claude/skills/novo-agente/quality-gate.sh [--strict]
#
# Checagens:
#   A  placeholder não renderizado ({SLUG} sobrando)     BLOCKER
#   B  architect COM Bash                                 BLOCKER
#   C  developer SEM Bash                                 BLOCKER
#   D  frontmatter sem name/description/tools             BLOCKER
#   E  agente sem menção à doutrina                       IMPORTANT
#
# Exit: 0 ok (ou sem --strict) · 7 --strict com BLOCKER · 2 erro de uso
#
# Por que B e C são BLOCKER: a separação architect/developer é a mesma cerca
# do projeto — quem planeja não executa. Um architect com Bash pode "só testar"
# e alterar estado.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
AGENTS="${REPO}/.claude/agents"
STRICT=0
[[ "${1:-}" == "--strict" ]] && STRICT=1

BLOCKERS=0
IMPORTANTES=0

achado() {
  local sev="$1" arquivo="$2" msg="$3"
  printf "  [%-9s] %-28s %s\n" "$sev" "$(basename "$arquivo")" "$msg"
  case "$sev" in
    BLOCKER)   BLOCKERS=$((BLOCKERS + 1)) ;;
    IMPORTANT) IMPORTANTES=$((IMPORTANTES + 1)) ;;
  esac
}

echo "quality-gate · .claude/agents/"
echo "────────────────────────────────────────────────────────────"

shopt -s nullglob
agentes=("${AGENTS}"/*.md)
if [[ ${#agentes[@]} -eq 0 ]]; then
  echo "  nenhum agente encontrado em .claude/agents/"
  exit 0
fi

for agente in "${agentes[@]}"; do
  nome="$(basename "$agente" .md)"

  # A — placeholder vazado
  if vazado="$(grep -oE '\{[A-Z_]+\}' "$agente" | sort -u | head -3 | tr '\n' ' ')"; then
    [[ -n "$vazado" ]] && achado BLOCKER "$agente" "placeholder não renderizado: $vazado"
  fi

  # D — frontmatter
  linha_tools="$(grep -m1 '^tools:' "$agente" || true)"
  grep -qE '^name:' "$agente"        || achado BLOCKER "$agente" "frontmatter sem 'name:'"
  grep -qE '^description:' "$agente" || achado BLOCKER "$agente" "frontmatter sem 'description:'"
  [[ -n "$linha_tools" ]]            || achado BLOCKER "$agente" "frontmatter sem 'tools:'"

  # B / C — a separação que importa
  if [[ "$nome" == *-architect ]]; then
    [[ "$linha_tools" == *Bash* ]] && \
      achado BLOCKER "$agente" "architect NÃO pode ter Bash — quem planeja não executa"
  elif [[ "$nome" == *-developer ]]; then
    [[ "$linha_tools" != *Bash* ]] && \
      achado BLOCKER "$agente" "developer PRECISA de Bash para rodar as evals"
  fi

  # E — a doutrina entrou?
  grep -qiE 'doutrina|DF-INSS|gate' "$agente" || \
    achado IMPORTANT "$agente" "não menciona doutrina, defeitos nem gates"
done

echo "────────────────────────────────────────────────────────────"
echo "  agentes verificados : ${#agentes[@]}"
echo "  BLOCKER             : ${BLOCKERS}"
echo "  IMPORTANT           : ${IMPORTANTES}"
echo ""

if [[ "${BLOCKERS}" -gt 0 ]]; then
  echo "  VEREDITO: BLOCK"
  if [[ "${STRICT}" -eq 1 ]]; then
    exit 7
  fi
elif [[ "${IMPORTANTES}" -gt 0 ]]; then
  echo "  VEREDITO: APROVA COM RESSALVAS"
else
  echo "  VEREDITO: APROVA"
fi
exit 0
