#!/usr/bin/env python3
"""A fábrica gerada é coerente consigo mesma?

Um gerador que produz um Makefile citando scripts inexistentes falha em
silêncio: a árvore parece completa, o git commita, e só quem roda `make`
descobre. Este script confere a fábrica RECÉM-GERADA antes de entregá-la.

O que se verifica:
  1. todo script citado no Makefile existe
  2. o contrato nasce NAO_MEDIDO e o gate de estado recusa build
  3. as duas cercas concordam
  4. nenhum placeholder {{VAR}} vazou para dentro de um arquivo
  5. o contrato é YAML válido

Uso:
  python3 verificar_fabrica.py <caminho-da-fabrica>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: verificar_fabrica.py <caminho-da-fabrica>")
        return 1
    fab = Path(sys.argv[1])
    if not fab.is_dir():
        print(f"não é diretório: {fab}")
        return 1

    problemas: list[str] = []
    avisos: list[str] = []

    # ── 1. scripts citados no Makefile existem ───────────────────────
    mk = fab / "Makefile"
    if not mk.exists():
        problemas.append("sem Makefile")
    else:
        txt = mk.read_text(encoding="utf-8")
        citados = set(re.findall(r"(?:scripts|ingestion)/[\w_]+\.(?:py|sh)", txt))
        for rel in sorted(citados):
            if not (fab / rel).exists():
                problemas.append(f"Makefile cita {rel}, que não existe")

    # ── 2. o contrato nasce NAO_MEDIDO ───────────────────────────────
    contrato = fab / "contracts" / "layout.yaml"
    if not contrato.exists():
        problemas.append("sem contracts/layout.yaml — a fábrica não tem juiz")
    else:
        try:
            c = yaml.safe_load(contrato.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            problemas.append(f"contrato não é YAML válido: {str(e)[:80]}")
            c = None
        if c is not None:
            if c.get("medido"):
                problemas.append(
                    "contrato nasce medido: true — deveria nascer NAO_MEDIDO. "
                    "Uma fábrica que constrói sem ninguém ter medido a fonte "
                    "publica ACEITO comparando contra nada."
                )
            if c.get("controle_por_particao"):
                problemas.append("contrato nasce com âncora — não foi medida por ninguém")

    # ── 3. o gate de estado realmente recusa ─────────────────────────
    estado = fab / "scripts" / "estado_contrato.py"
    if not estado.exists():
        problemas.append("sem scripts/estado_contrato.py — nada impede o build")
    else:
        r = subprocess.run(
            [sys.executable, "scripts/estado_contrato.py", "--exigir-medido"],
            cwd=fab, capture_output=True, text=True,
        )
        if r.returncode == 0:
            problemas.append(
                "estado_contrato.py --exigir-medido saiu 0 num contrato "
                "NAO_MEDIDO: o gate não recusa nada"
            )

    # ── 4. placeholder vazado ────────────────────────────────────────
    for p in fab.rglob("*"):
        if not p.is_file() or ".git/" in str(p):
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        achados = sorted(set(re.findall(r"\{\{([A-Z_]+)\}\}", t)))
        if achados:
            # templates da skill novo-agente usam {{VAR}} legitimamente
            if ".claude/skills/" in str(p):
                continue
            problemas.append(f"{p.relative_to(fab)}: placeholder {achados}")

    # ── 5. o manual existe e cobre o caminho inteiro ─────────────────
    # Uma fábrica sem manual entrega disciplina que ninguém sabe operar.
    # Pior: os 8 scripts semente NÃO rodam como estão, e sem o manual não
    # há nada dizendo isso.
    manual = fab / "docs" / "MANUAL.md"
    if not manual.exists():
        problemas.append("sem docs/MANUAL.md — ninguém sabe por onde começar")
    else:
        txt = manual.read_text(encoding="utf-8")
        for passo in ("make init", "make fetch", "make perfil", "make ancora",
                      "make contrato", "make all", "make evals"):
            if passo not in txt:
                problemas.append(f"MANUAL.md não cobre `{passo}`")
        # O manual tem de avisar sobre as sementes e sobre o ~?, senão
        # entrega uma fábrica que parece pronta e não está.
        if "SEMENTE" not in txt:
            problemas.append("MANUAL.md não avisa que há scripts a adaptar")
        if "ACEITO_SEM_ANCORA" not in txt:
            problemas.append("MANUAL.md não explica ACEITO_SEM_ANCORA (~?)")

    # ── 6. as duas cercas concordam ──────────────────────────────────
    cercas = fab / "scripts" / "verificar_cercas.py"
    if cercas.exists():
        r = subprocess.run([sys.executable, "scripts/verificar_cercas.py"],
                           cwd=fab, capture_output=True, text=True)
        if r.returncode != 0:
            problemas.append(f"cercas divergem: {r.stdout.strip()[:200]}")
    else:
        avisos.append("sem verificar_cercas.py")

    # ── 7. settings.json é JSON válido ───────────────────────────────
    st = fab / ".claude" / "settings.json"
    if st.exists():
        try:
            json.loads(st.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problemas.append(f"settings.json inválido: {e}")

    # ── relatório ────────────────────────────────────────────────────
    print(f"── verificação de {fab.name} ──")
    for a in avisos:
        print(f"  aviso   {a}")
    if problemas:
        print(f"\n  {len(problemas)} PROBLEMA(S):")
        for p in problemas:
            print(f"    - {p}")
        print("\n  A fábrica gerada NÃO está coerente. Corrija a skill —")
        print("  não a fábrica: ela é regenerável, a skill é a fonte.")
        return 1

    print("  OK · Makefile coerente · contrato NAO_MEDIDO · gate recusa · "
          "manual completo · cercas concordam")
    return 0


if __name__ == "__main__":
    sys.exit(main())
