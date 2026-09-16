#!/usr/bin/env python3
"""Ranking — concentração bancária a partir do Gold.

Só lê. Não recalcula agregado: o Gold já passou pelos gates.

O banco 998 (INSS pagando direto) fica FORA do ranking por decisão do
ADR 0005 — mas aparece ao final, porque quanto do pagamento não passa
por instituição financeira é informação, não ruído.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import yaml

BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="top bancos por valor pago")
    ap.add_argument("--competencia")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--uf", help="filtra uma UF (ex: 'São Paulo')")
    args = ap.parse_args()

    contrato = yaml.safe_load((BASE / "contracts" / "layout.yaml").read_text(encoding="utf-8"))
    comp = args.competencia or contrato["competencia"]

    db = BASE / "lakehouse" / comp / "inss.duckdb"
    if not db.exists():
        print(f"sem Gold para {comp} — rode: make all COMP={comp}")
        return 1

    con = duckdb.connect(str(db), read_only=True)
    filtro_uf = "and uf_residencia = ?" if args.uf else ""
    params = [args.uf] if args.uf else []

    total = con.execute(
        f"select sum(vl_total) from gold_concentracao_bancaria where 1=1 {filtro_uf}",
        params,
    ).fetchone()[0]

    linhas = con.execute(
        f"""select banco_codigo, max(banco_nome), sum(qtd_beneficios), sum(vl_total)
            from gold_concentracao_bancaria
            where not e_inss_direto {filtro_uf}
            group by banco_codigo
            order by 4 desc limit {args.top}""",
        params,
    ).fetchall()

    escopo = args.uf or "nacional"
    print(f"\n  Concentração bancária · {comp} · {escopo}")
    print(f"  total pago: R$ {total:,.2f}\n")
    acumulado = 0
    for i, (cod, nome, _qtd, valor) in enumerate(linhas, 1):
        pct = 100 * float(valor) / float(total)
        acumulado += pct
        print(f"  {i:>2}. {cod}  {nome:22} R$ {valor:>17,.2f}  {pct:>5.2f}%")
    print(f"\n  TOP {len(linhas)} acumulam {acumulado:.2f}%")

    direto = con.execute(
        f"""select sum(qtd_beneficios), sum(vl_total)
            from gold_concentracao_bancaria
            where e_inss_direto {filtro_uf}""",
        params,
    ).fetchone()
    if direto and direto[1]:
        pct = 100 * float(direto[1]) / float(total)
        print("\n  fora do ranking (ADR 0005):")
        print(f"      998  INSS pagando direto    "
              f"R$ {direto[1]:>17,.2f}  {pct:>5.2f}%  ·  {direto[0]:,} benefícios")
    con.close()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
