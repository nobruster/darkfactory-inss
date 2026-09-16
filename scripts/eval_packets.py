#!/usr/bin/env python3
"""eval-1 — os três packets da competência saem ACEITO e publicados.

Verifica B-1. Exit 0 = passou.
Não recalcula nada: lê a evidência que a execução deixou.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia", default="2026-01")
    args = ap.parse_args()
    aaaamm = args.competencia.replace("-", "")

    erros: list[str] = []
    for camada in ("bronze", "silver", "gold"):
        f = BASE / "evidence" / f"{camada}-{aaaamm}.json"
        if not f.exists():
            erros.append(f"{camada}: packet ausente ({f.name})")
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("status") != "ACEITO":
            erros.append(f"{camada}: status={d.get('status')} falhas={d.get('falhas')}")
        if d.get("publicado") is not True:
            erros.append(f"{camada}: não publicado")

    if erros:
        print("eval-1 FALHOU")
        for e in erros:
            print(f"  - {e}")
        return 1
    print("eval-1 OK · 3 packets ACEITO e publicados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
