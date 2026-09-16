#!/usr/bin/env python3
"""Status — o que rodou, em que competência, com que resultado.

Lê os packets de evidence/ e mostra a linha completa por competência.
Não recalcula nada: só relata o que está registrado no disco.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PADRAO = re.compile(r"^(fetch|bronze|silver|gold)-(\d{6})\.json$")
ORDEM = ["fetch", "bronze", "silver", "gold"]


def main() -> int:
    packets: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in sorted((BASE / "evidence").glob("*.json")):
        m = PADRAO.match(f.name)
        if not m:
            continue
        camada, aaaamm = m.groups()
        comp = f"{aaaamm[:4]}-{aaaamm[4:]}"
        try:
            packets[comp][camada] = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            packets[comp][camada] = {"status": "ILEGÍVEL"}

    if not packets:
        print("nenhum packet — rode: make all")
        return 0

    for comp in sorted(packets):
        print(f"\n  {comp}")
        for camada in ORDEM:
            d = packets[comp].get(camada)
            if d is None:
                print(f"    {camada:8} —")
                continue
            st = d.get("status", "?")
            # ACEITO_SEM_ANCORA é publicação legítima, mas SEM juiz de total:
            # merece marca própria. Confundi-la com ACEITO seria repetir o
            # erro que a auditoria de 16/09/2026 encontrou (objeção #28).
            marca = {"ACEITO": "OK ", "ACEITO_SEM_ANCORA": "~? "}.get(st, "!! ")
            extra = ""
            if camada == "bronze":
                extra = f"{d.get('linhas', 0):,} linhas · {d.get('sum_vl_liquido', '')}"
            elif camada == "silver":
                orf = (d.get("DF-INSS-003") or {}).get("codigos_orfaos") or []
                extra = f"{d.get('linhas', 0):,} linhas"
                if orf:
                    extra += f" · órfãos {orf}"
            elif camada == "gold":
                extra = f"{d.get('linhas', 0)} agregados · {d.get('sum_vl_total', '')}"
            elif camada == "fetch":
                extra = f"{d.get('zip_bytes', 0):,} bytes"
            print(f"    {marca}{camada:8} {st:18} {extra}")
            if st != "ACEITO":
                for falha in d.get("falhas", []):
                    print(f"             ↳ {falha}")
                if d.get("aviso"):
                    print(f"             ↳ {d['aviso']}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
