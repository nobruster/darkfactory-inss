#!/usr/bin/env python3
"""eval-3 — a doutrina foi respeitada.

Verifica B-4 (espécie pelo código), B-5 (banco 998 fora do ranking),
B-6 (27 UFs, grão único) e B-7 (pastas congeladas intactas).

Executa contra o lakehouse real, não contra o packet. Se alguém reintroduzir
o agrupamento por nome, o número de rótulos cai e esta eval reprova.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import duckdb

BASE = Path(__file__).resolve().parents[1]
CONGELADOS = ["_raw/", "contracts/", "docs/adrs/"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia", default="2026-01")
    args = ap.parse_args()

    db = BASE / "lakehouse" / args.competencia / "inss.duckdb"
    if not db.exists():
        print(f"eval-3 FALHOU · sem lakehouse para {args.competencia}")
        return 1

    con = duckdb.connect(str(db), read_only=True)
    q = lambda s: con.execute(s).fetchone()[0]
    erros: list[str] = []

    # B-4 — espécie resolvida pelo código, não pelo nome truncado.
    # Se agruparem pelo nome, rótulos <= truncados e o total continua batendo:
    # é justamente esse erro silencioso que esta comparação detecta.
    rotulos = q("select count(distinct especie_rotulo) from silver where not especie_orfa")
    truncados = q("select count(distinct especie_nome_fonte) from silver")
    if rotulos <= truncados:
        erros.append(f"B-4: rótulos {rotulos} <= nomes truncados {truncados} "
                     f"— agrupamento por nome?")

    # B-5 — o banco 998 é o INSS pagando direto, não instituição financeira
    ranqueado = q("""select count(*) from gold_concentracao_bancaria
                     where e_inss_direto and posicao_na_uf is not null""")
    if ranqueado:
        erros.append(f"B-5: banco 998 ranqueado em {ranqueado} UFs")
    if not q("select count(*) from gold_concentracao_bancaria where e_inss_direto"):
        erros.append("B-5: banco 998 ausente — deveria ter linha própria")

    # B-6 — cobertura nacional e grão único
    ufs = q("select count(distinct uf_residencia) from gold_concentracao_bancaria")
    if ufs != 27:
        erros.append(f"B-6: {ufs} UFs, esperado 27")
    dup = q("""select count(*) from (
                 select 1 from gold_concentracao_bancaria
                 group by competencia, banco_codigo, uf_residencia
                 having count(*) > 1)""")
    if dup:
        erros.append(f"B-6: grão duplicado em {dup} combinações")

    con.close()

    # B-7 — nada foi escrito nas pastas congeladas
    sujo = subprocess.run(
        ["git", "-C", str(BASE), "status", "--short", *CONGELADOS],
        capture_output=True, text=True,
    ).stdout.strip()
    if sujo:
        erros.append(f"B-7: pasta congelada alterada:\n      "
                     + sujo.replace("\n", "\n      "))

    if erros:
        print("eval-3 FALHOU")
        for e in erros:
            print(f"  - {e}")
        return 1

    print(f"eval-3 OK · {rotulos} rótulos > {truncados} truncados · "
          f"998 fora do ranking · {ufs} UFs · congelados intactos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
