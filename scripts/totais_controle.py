#!/usr/bin/env python3
"""Totais de controle da fonte — a âncora de integridade da fábrica.

Varre as ~41M linhas e mede count, soma, mínimo e máximo. Estes números
viram `controle:` no contrato, e todo gate de valor os usa como referência.

Medir, nunca estimar: um número no contrato que ninguém consegue reproduzir
não é âncora, é palpite.

Uso:
  python3 scripts/totais_controle.py --competencia 2026-03
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="mede os totais de controle da fonte")
    ap.add_argument("--competencia", help="AAAA-MM; padrão: a do contrato")
    args = ap.parse_args()

    contrato = yaml.safe_load(
        (BASE / "contracts" / "layout.yaml").read_text(encoding="utf-8")
    )
    comp = args.competencia or contrato["competencia"]
    aaaamm = comp.replace("-", "")
    fonte = BASE / "_raw" / f"fonte-{aaaamm}.zip"
    if not fonte.exists():
        print(f"sem fonte para {comp}. rode antes:")
        print(f"  python3 ingestion/fetch_fonte.py --competencia {comp}")
        return 1

    ncols = contrato["fonte"]["colunas"]
    total = 0
    soma = Decimal("0")
    invalidas = 0
    menor: Decimal | None = None
    maior: Decimal | None = None
    t0 = time.time()

    with zipfile.ZipFile(fonte) as z:
        membro = z.namelist()[0]
        with z.open(membro) as f:
            texto = io.TextIOWrapper(f, encoding=contrato["fonte"]["encoding"])
            texto.readline()  # cabeçalho
            for linha in texto:
                partes = linha.rstrip("\r\n").split(";")
                if len(partes) < ncols:
                    invalidas += 1
                    continue
                total += 1
                bruto = partes[9].strip().replace(".", "").replace(",", ".")
                try:
                    valor = Decimal(bruto)
                except (InvalidOperation, ValueError):
                    invalidas += 1
                    continue
                soma += valor
                if menor is None or valor < menor:
                    menor = valor
                if maior is None or valor > maior:
                    maior = valor
                if total % 10_000_000 == 0:
                    print(f"  {total:,} linhas · {time.time() - t0:.0f}s", flush=True)

    saida = {
        "competencia": comp,
        "count_linhas": total,
        "linhas_invalidas": invalidas,
        "sum_vl_liquido": str(soma),
        "min_vl_liquido": str(menor),
        "max_vl_liquido": str(maior),
        "segundos": round(time.time() - t0),
    }
    destino = BASE / "evidence" / f"_totais-{aaaamm}.json"
    destino.write_text(json.dumps(saida, indent=2), encoding="utf-8")

    print()
    print(json.dumps(saida, indent=2))
    print(f"\n  {destino.relative_to(BASE)}")

    # Se for a competência que o contrato declara, compara — é a âncora.
    if comp == contrato["competencia"]:
        ctl = contrato["controle"]
        divergiu = []
        if total != ctl["count_linhas"]:
            divergiu.append(f"count medido {total} != contrato {ctl['count_linhas']}")
        if str(soma) != ctl["sum_vl_liquido"]:
            divergiu.append(f"soma medida {soma} != contrato {ctl['sum_vl_liquido']}")
        print()
        if divergiu:
            print("  ⚠ DIVERGE DO CONTRATO:")
            for d in divergiu:
                print(f"    - {d}")
            print("    A fonte mudou ou o contrato está errado. Investigue —")
            print("    não ajuste o contrato sem entender qual dos dois mudou.")
            return 1
        print("  confere com o contrato")
    return 0


if __name__ == "__main__":
    sys.exit(main())
