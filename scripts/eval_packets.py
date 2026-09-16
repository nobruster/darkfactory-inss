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
        # ACEITO_SEM_ANCORA é publicação legítima de competência ainda não
        # ancorada — mas não passa nesta eval: eval-1 exige a linha completa.
        if d.get("status") != "ACEITO":
            erros.append(f"{camada}: status={d.get('status')} falhas={d.get('falhas')}")
        if d.get("publicado") is not True:
            erros.append(f"{camada}: não publicado")
        # ⚠ Um packet ACEITO com gate de ÂNCORA false mente por omissão: quem
        # lê o status não vê que o gate nem rodou. Foi assim que 82 milhões de
        # linhas foram publicadas sem conferência contra a fonte.
        # Auditoria de 16/09/2026, objeção #28.
        #
        # Nem todo `false` é gate desligado. `numeros_do_contrato_conferidos`
        # e `soma_confere_contrato` significam "esta não é a competência que o
        # contrato declara" — é informação de escopo, e a âncora por
        # competência já cobre o total. Só os gates abaixo são inegociáveis.
        gates = d.get("gates") or {}
        ANCORA = {
            "count_confere", "soma_confere",            # bronze
            "count_confere_ancora", "soma_confere_ancora",   # silver
            "qtd_confere_ancora",                        # gold
            "count_confere_bronze", "soma_confere_bronze",
            "soma_confere_silver", "qtd_confere_silver",
            "rejeicoes_zero", "grao_unico",
        }
        desligados = [k for k in ANCORA if gates.get(k) is False]
        if desligados:
            erros.append(f"{camada}: ACEITO com gate de âncora desligado -> "
                         f"{sorted(desligados)}. "
                         f"Gate que não rodou não é gate que passou.")

    if erros:
        print("eval-1 FALHOU")
        for e in erros:
            print(f"  - {e}")
        return 1
    print("eval-1 OK · 3 packets ACEITO e publicados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
