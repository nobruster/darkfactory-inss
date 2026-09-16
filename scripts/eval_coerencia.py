#!/usr/bin/env python3
"""eval-2 — o valor e a contagem atravessam as camadas sem divergir.

Verifica B-2 (soma) e B-3 (contagem). Tolerância ZERO — sem banda.
Usa Decimal: comparar dinheiro com float faria esta eval passar por acaso.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia", default="2026-01")
    args = ap.parse_args()
    aaaamm = args.competencia.replace("-", "")

    def packet(camada: str) -> dict:
        return json.loads(
            (BASE / "evidence" / f"{camada}-{aaaamm}.json").read_text(encoding="utf-8")
        )

    try:
        b, s, g = packet("bronze"), packet("silver"), packet("gold")
    except FileNotFoundError as e:
        print(f"eval-2 FALHOU · packet ausente: {e.filename}")
        return 1

    somas = {
        "bronze": Decimal(b["sum_vl_liquido"]),
        "silver": Decimal(s["sum_vl_liquido"]),
        "gold": Decimal(g["sum_vl_total"]),
    }
    contagens = {
        "bronze": b["linhas"],
        "silver": s["linhas"],
        "gold": g["qtd_beneficios"],
    }

    erros: list[str] = []
    if len(set(somas.values())) != 1:
        erros.append("soma divergiu entre camadas: "
                     + " · ".join(f"{k}={v}" for k, v in somas.items()))
    if len(set(contagens.values())) != 1:
        erros.append("contagem divergiu entre camadas: "
                     + " · ".join(f"{k}={v:,}" for k, v in contagens.items()))

    if erros:
        print("eval-2 FALHOU")
        for e in erros:
            print(f"  - {e}")
        return 1

    print(f"eval-2 OK · {contagens['bronze']:,} linhas · R$ {somas['bronze']} "
          f"idêntico nas 3 camadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
