#!/usr/bin/env bash
# scaffold.sh — gera uma Dark Factory completa a partir de uma entrada de menu.
#
#   bash .claude/skills/nova-fabrica/scaffold.sh <slug>
#   bash .claude/skills/nova-fabrica/scaffold.sh --diff <slug>   # mostra, não aplica
#   bash .claude/skills/nova-fabrica/scaffold.sh --dry-run <slug>
#
# A fábrica nasce em ~/darkfactory-<slug>, com git próprio e o contrato
# marcado NAO_MEDIDO. Ela RECUSA construir até alguém medir a fonte.
#
# Exit: 0 ok · 1 erro de uso · 2 slug ausente do menu · 3 destino já existe

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SKILL_DIR}/../../.." && pwd)"
MENU="${SKILL_DIR}/menu/fabricas.yaml"
PY="${REPO}/.venv/bin/python"
[[ -x "${PY}" ]] || PY="python3"

MODO="gerar"
SLUG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --diff)     MODO="diff";    shift ;;
    --dry-run)  MODO="dry-run"; shift ;;
    -h|--help)
      sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
      exit 0 ;;
    -*) echo "opção desconhecida: $1" >&2; exit 1 ;;
    *)  SLUG="$1"; shift ;;
  esac
done

if [[ -z "${SLUG}" ]]; then
  echo "uso: scaffold.sh <slug>   (slugs no menu: $(
    "${PY}" -c "
import yaml,sys
m = yaml.safe_load(open('${MENU}', encoding='utf-8')) or {}
print(', '.join(k for k in m if not k.startswith('_') and k != 'schema_version'))
" 2>/dev/null || echo '?')" >&2
  exit 1
fi

DESTINO="${HOME}/darkfactory-${SLUG}"

if [[ "${MODO}" == "gerar" && -e "${DESTINO}" ]]; then
  echo "recuso: ${DESTINO} já existe." >&2
  echo "  Uma fábrica com contrato medido e evidência publicada não se" >&2
  echo "  sobrescreve por script. Se é para recomeçar, mova a antiga." >&2
  exit 3
fi

if [[ "${MODO}" != "gerar" ]]; then
  echo "── ${MODO}: nada será escrito ──"
  DESTINO="$(mktemp -d)/darkfactory-${SLUG}"
fi

echo "gerando fábrica '${SLUG}'"
echo "  destino: ${DESTINO}"
echo ""

"${PY}" - "${SLUG}" "${MENU}" "${SKILL_DIR}" "${DESTINO}" "${REPO}" <<'PYEOF'
import datetime
import json
import pathlib
import shutil
import sys

try:
    import yaml
except ImportError:
    sys.exit("faltou pyyaml: .venv/bin/pip install pyyaml")

slug, menu_path, skill_dir, destino, repo = sys.argv[1:6]
skill_dir = pathlib.Path(skill_dir)
destino = pathlib.Path(destino)
repo = pathlib.Path(repo)

menu = yaml.safe_load(pathlib.Path(menu_path).read_text(encoding="utf-8")) or {}
f = menu.get(slug)
# `_exemplo_*` é documentação, não fábrica gerável. `_autoteste` é a exceção:
# existe justamente para o quality-gate gerar e conferir.
if slug.startswith("_") and slug != "_autoteste":
    sys.exit(f"'{slug}' começa com _ — é entrada de documentação, não gerável.")
if not f:
    disp = [k for k in menu if not k.startswith("_") and k != "schema_version"]
    sys.exit(f"'{slug}' não está no menu. Disponíveis: {', '.join(disp) or '(nenhum)'}")

# ── validação: o que o gerador NÃO adivinha ──────────────────────────
obrigatorios = ["display_name", "pergunta", "grao_gold"]
faltando = [c for c in obrigatorios if not f.get(c)]
fonte = f.get("fonte") or {}
if not fonte.get("url_padrao"):
    faltando.append("fonte.url_padrao")
if not fonte.get("formato"):
    faltando.append("fonte.formato")
if faltando:
    sys.exit(
        f"entrada '{slug}' incompleta: falta {', '.join(faltando)}.\n"
        f"  Estes campos o gerador NÃO inventa — sem eles a fábrica\n"
        f"  nasceria adivinhando o que devia medir."
    )

hoje = datetime.date.today().isoformat()

# `pergunta` é o que separa Gold de dump. Aviso, não bloqueio.
if len(f["pergunta"]) < 20 or "?" not in f["pergunta"]:
    print(f"  ⚠ pergunta curta ou sem '?': {f['pergunta']!r}")
    print("    O Gold responde uma pergunta. Sem ela, produz tabela grande.")
    print("")


def ylist(v):
    """Lista Python -> lista YAML inline. `[]` vira `[]`, não `null`."""
    return json.dumps(v or [], ensure_ascii=False)


def ymap(v):
    if not v:
        return "{}"
    linhas = [""]
    for k, desc in v.items():
        linhas.append(f'  "{k}": "{desc}"')
    return "\n".join(linhas)


subs = {
    "SLUG": slug,
    "SLUG_UPPER": slug.upper().replace("-", ""),
    "DISPLAY_NAME": f["display_name"],
    "PERGUNTA": f["pergunta"],
    "DATA": hoje,
    "URL_PADRAO": fonte["url_padrao"],
    "FORMATO": fonte["formato"],
    "ENCODING": fonte.get("encoding", "latin-1"),
    "SEPARADOR": fonte.get("separador", ";"),
    "TEM_CABECALHO": str(fonte.get("tem_cabecalho", True)).lower(),
    "LEITURA": fonte.get("leitura", "posicional"),
    "PARTICAO": fonte.get("particao", "competencia"),
    "PARTICAO_EXEMPLO": fonte.get("particao_exemplo", "2026-01"),
    "GRAO_SILVER": ylist(f.get("grao_silver")),
    "GRAO_GOLD": ylist(f["grao_gold"]),
    "COLUNAS_MONETARIAS": ylist(f.get("colunas_monetarias")),
    "CHAVES_SUSPEITAS": ylist(f.get("chaves_suspeitas")),
    "SENTINELAS": ymap(f.get("sentinelas")),
    "DEDUP": "proibida" if f.get("deduplicacao_proibida") else "permitida",
    "MOTIVO_DEDUP": f.get("motivo_dedup", "não declarado — decida antes do Silver"),
}


def render(texto: str) -> str:
    for k, v in subs.items():
        texto = texto.replace("{{" + k + "}}", str(v))
        # {{VAR}} não substituído é bug silencioso: o arquivo sai com o
        # placeholder literal e ninguém percebe até o gate reclamar.
    return texto


# ── estrutura ────────────────────────────────────────────────────────
PASTAS = [
    "contracts", "ingestion", "scripts", "tests", "evidence",
    "docs/adrs", "landing", "lakehouse", "_raw",
    ".claude/agents", ".claude/skills", ".cvg", ".github/workflows",
]
for p in PASTAS:
    (destino / p).mkdir(parents=True, exist_ok=True)

escritos = []


def escrever(rel: str, conteudo: str, executavel: bool = False):
    alvo = destino / rel
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(conteudo, encoding="utf-8")
    if executavel:
        alvo.chmod(0o755)
    escritos.append(rel)


# ── 1. templates próprios da skill ───────────────────────────────────
TPL = skill_dir / "templates"
MAPA_TPL = {
    "layout.yaml.tpl": "contracts/layout.yaml",
    "Makefile.tpl": "Makefile",
    "estado_contrato.py.tpl": "scripts/estado_contrato.py",
    "promover_medicao.py.tpl": "scripts/promover_medicao.py",
    "CLAUDE.md.tpl": "CLAUDE.md",
    "README.md.tpl": "README.md",
    "gate.yaml.tpl": ".cvg/gate.yaml",
    "settings.json.tpl": ".claude/settings.json",
    "qualidade.yml.tpl": ".github/workflows/qualidade.yml",
    "gitignore.tpl": ".gitignore",
    "pyproject.toml.tpl": "pyproject.toml",
}
for tpl, alvo in MAPA_TPL.items():
    origem = TPL / tpl
    if not origem.exists():
        print(f"  ⚠ template ausente: {tpl} — {alvo} não foi gerado")
        continue
    escrever(alvo, render(origem.read_text(encoding="utf-8")))

# ── 2. scripts herdados do INSS, com a doutrina já dentro ────────────
# Copiados como SEMENTE: o cabeçalho de cada um avisa que foi gerado e
# que a lógica específica da fonte é do dono da fábrica.
HERDADOS = {
    # doutrina pura — funcionam em qualquer fábrica sem adaptação
    "scripts/verificar_cercas.py": "scripts/verificar_cercas.py",
    "scripts/refrescar_checksums.py": "scripts/refrescar_checksums.py",
    "scripts/rodar_evals.sh": "scripts/rodar_evals.sh",
    "scripts/rodar_evals_todas.sh": "scripts/rodar_evals_todas.sh",
    "scripts/eval_packets.py": "scripts/eval_packets.py",
    "scripts/eval_coerencia.py": "scripts/eval_coerencia.py",
    "scripts/status.py": "scripts/status.py",
    "scripts/ancorar_bronze.py": "scripts/ancorar_bronze.py",
    # ── ADAPTAR: a lógica da fonte é específica, a estrutura não ──
    # Vêm como semente porque escrever do zero é pior: o autor esquece
    # publicação atômica, esquece o gate de âncora, esquece ZERO artefato
    # na rejeição. Aqui ele começa com tudo isso e troca o que é da fonte.
    "ingestion/fetch_fonte.py": "ingestion/fetch_fonte.py",
    "ingestion/ingest_bronze.py": "ingestion/ingest_bronze.py",
    "scripts/perfil_cobertura.py": "scripts/perfil_cobertura.py",
    "scripts/totais_controle.py": "scripts/totais_controle.py",
    "scripts/build_silver.py": "scripts/build_silver.py",
    "scripts/build_gold.py": "scripts/build_gold.py",
    "scripts/eval_doutrina.py": "scripts/eval_doutrina.py",
    "tests/test_ancora.py": "tests/test_ancora.py",
}

# Estes precisam de adaptação à fonte nova. O aviso é mais forte: não é só
# procedência, é "isto ainda fala do INSS e vai quebrar".
ADAPTAR = {
    "ingestion/fetch_fonte.py", "ingestion/ingest_bronze.py",
    "scripts/perfil_cobertura.py", "scripts/totais_controle.py",
    "scripts/build_silver.py", "scripts/build_gold.py",
    "scripts/eval_doutrina.py", "tests/test_ancora.py",
}
AVISO_DOUTRINA = (
    "# ─────────────────────────────────────────────────────────────\n"
    f"# SEMENTE gerada por nova-fabrica em {hoje}, a partir do\n"
    "# darkfactory-inss. Este arquivo é doutrina pura: funciona nesta\n"
    "# fábrica sem adaptação. Se você mudá-lo, apague este aviso para\n"
    "# não mentir sobre a procedência.\n"
    "# ─────────────────────────────────────────────────────────────\n"
)
AVISO_ADAPTAR = (
    "# ═════════════════════════════════════════════════════════════\n"
    f"# ⚠ SEMENTE A ADAPTAR — gerada por nova-fabrica em {hoje}.\n"
    "#\n"
    "# A ESTRUTURA está certa e você deve preservá-la:\n"
    "#   · publicação atômica (.parcial + rename)\n"
    "#   · ZERO artefato quando um gate reprova\n"
    "#   · gate de âncora que NUNCA se desliga sozinho\n"
    "#   · packet de evidência em toda execução\n"
    "#\n"
    "# A LÓGICA ainda fala do INSS: nomes de coluna, parsing, regra de\n"
    "# negócio. Isto NÃO roda como está — adapte à sua fonte.\n"
    "#\n"
    "# Veio como semente porque escrever do zero é pior: quem começa em\n"
    "# branco esquece a publicação atômica e o gate de âncora, e descobre\n"
    "# meses depois numa auditoria.\n"
    "#\n"
    "# Ao terminar de adaptar, apague este bloco.\n"
    "# ═════════════════════════════════════════════════════════════\n"
)
for origem_rel, alvo_rel in HERDADOS.items():
    origem = repo / origem_rel
    if not origem.exists():
        print(f"  ⚠ não encontrei {origem_rel} no repo-fonte")
        continue
    txt = origem.read_text(encoding="utf-8")
    linhas = txt.split("\n")
    # o aviso entra depois do shebang, senão quebra a execução
    corte = 1 if linhas and linhas[0].startswith("#!") else 0
    aviso = AVISO_ADAPTAR if origem_rel in ADAPTAR else AVISO_DOUTRINA
    novo = "\n".join(linhas[:corte]) + ("\n" if corte else "") + aviso + \
           "\n".join(linhas[corte:])
    escrever(alvo_rel, novo, executavel=origem_rel.endswith(".sh"))

# ── 3. o gerador de agentes vai junto ────────────────────────────────
origem_skill = repo / ".claude" / "skills" / "novo-agente"
if origem_skill.exists():
    shutil.copytree(origem_skill, destino / ".claude/skills/novo-agente",
                    dirs_exist_ok=True)
    escritos.append(".claude/skills/novo-agente/ (copiada)")

# ── 4. ADRs semente ──────────────────────────────────────────────────
ADRS = skill_dir / "templates" / "adrs"
if ADRS.exists():
    for adr in sorted(ADRS.glob("*.md.tpl")):
        escrever(f"docs/adrs/{adr.name[:-4]}",
                 render(adr.read_text(encoding="utf-8")))

# ── 5. .gitkeep nas pastas que nascem vazias ─────────────────────────
for p in ("evidence", "landing", "lakehouse", "_raw"):
    (destino / p / ".gitkeep").write_text("", encoding="utf-8")

# ── verificação: placeholder não substituído é bug ───────────────────
import re
vazando = []
for rel in escritos:
    alvo = destino / rel
    if not alvo.is_file():
        continue
    try:
        txt = alvo.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    achados = set(re.findall(r"\{\{([A-Z_]+)\}\}", txt))
    if achados:
        vazando.append((rel, sorted(achados)))

print(f"  {len(escritos)} arquivos gerados")
if vazando:
    print("")
    print("  ⚠ PLACEHOLDER NÃO SUBSTITUÍDO — a fábrica saiu incompleta:")
    for rel, ph in vazando:
        print(f"    {rel}: {', '.join(ph)}")
    sys.exit(1)

print(f"  contrato: NAO_MEDIDO (é assim que tem de nascer)")
PYEOF

RC=$?
if [[ ${RC} -ne 0 ]]; then
  echo "" >&2
  echo "geração FALHOU — nada confiável foi produzido." >&2
  exit ${RC}
fi

if [[ "${MODO}" != "gerar" ]]; then
  echo ""
  echo "── ${MODO}: árvore gerada em ${DESTINO} ──"
  find "${DESTINO}" -type f | sed "s|${DESTINO}|  .|" | sort
  exit 0
fi

# ── git init: a fábrica nasce versionada ───────────────────────────
cd "${DESTINO}"
git init -q
git add -A
git -c user.email="$(git -C "${REPO}" config user.email 2>/dev/null || echo nobruster@gmail.com)" \
    -c user.name="$(git -C "${REPO}" config user.name 2>/dev/null || echo Bruno)" \
    commit -q -m "fábrica ${SLUG}: esqueleto gerado, contrato NAO_MEDIDO

Gerada por nova-fabrica a partir do darkfactory-inss.

O contrato nasce sem números e a fábrica RECUSA construir até que
alguém meça a fonte. Não é pendência a resolver depois: é o primeiro
gate, e ele é contra a própria fábrica.

Próximo passo:
  make init && make fetch && make perfil && make ancora && make contrato"

echo ""
echo "  fábrica criada e versionada em ${DESTINO}"
echo ""
echo "  Próximo passo — a fábrica não constrói até você medir:"
echo ""
echo "    cd ${DESTINO}"
echo "    make init"
echo "    make fetch     # baixa e congela a fonte"
echo "    make perfil    # mede layout, domínios, cobertura"
echo "    make ancora    # mede count e soma direto da fonte"
echo "    make contrato  # transfere o medido para o contrato"
echo ""
