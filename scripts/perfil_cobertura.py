#!/usr/bin/env python3
"""Perfila a fonte de uma competência: UFs, bancos, espécies.

Varre as ~41M linhas em streaming e conta cardinalidade. Serve para
descobrir o que existe antes de declarar domínio no contrato.

Não altera nada. Escreve só em evidence/_perfil-cobertura.json.

Uso:
  python3 scripts/perfil_cobertura.py --competencia 2026-03
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="perfila UFs, bancos e espécies da fonte")
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

    ufs: collections.Counter = collections.Counter()
    bancos: collections.Counter = collections.Counter()
    especies: collections.Counter = collections.Counter()
    total = 0
    t0 = time.time()

    with zipfile.ZipFile(fonte) as z:
        membro = z.namelist()[0]
        with z.open(membro) as f:
            texto = io.TextIOWrapper(f, encoding=contrato["fonte"]["encoding"])
            texto.readline()  # cabeçalho
            for linha in texto:
                partes = linha.split(";")
                if len(partes) < contrato["fonte"]["colunas"]:
                    continue
                ufs[partes[4].strip()] += 1
                bancos[partes[6].strip()] += 1
                especies[partes[12].strip()] += 1
                total += 1
                if total % 5_000_000 == 0:
                    print(f"  {total:,} linhas · {time.time() - t0:.0f}s · "
                          f"UFs={len(ufs)}", flush=True)

    saida = {
        "competencia": comp,
        "total_linhas": total,
        "ufs": dict(ufs),
        "bancos": dict(bancos),
        "especies": dict(especies),
        "segundos": round(time.time() - t0),
    }
    destino = BASE / "evidence" / f"_perfil-{aaaamm}.json"
    destino.write_text(
        json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{comp} · {total:,} linhas · {len(ufs)} UFs · "
          f"{len(bancos)} bancos · {len(especies)} espécies · "
          f"{time.time() - t0:.0f}s")
    print(f"  {destino.relative_to(BASE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
