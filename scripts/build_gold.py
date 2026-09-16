#!/usr/bin/env python3
"""Gold — concentração bancária por UF.

Pergunta que responde:
    Quanto cada instituição financeira movimenta em benefícios do INSS,
    por unidade federativa?

Contrato (contracts/layout.yaml):
  - grão: (competencia, banco_codigo, uf_residencia) — único, sem duplicata
  - sum(gold.vl_total) == sum(silver.vl_liquido)   tolerância ZERO
  - 27 UFs presentes
  - banco 998 (INSS-DIRETO) é linha própria, JAMAIS agregado a banco
  - o ranking exclui o 998: ele não é instituição financeira

Reconstrói só a partir do Silver. Não lê a fonte nem o Bronze.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import yaml

BASE = Path("/home/nobru/darkfactory-inss")


def main() -> int:
    contrato = yaml.safe_load((BASE / "contracts" / "layout.yaml").read_text(encoding="utf-8"))
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia")
    args = ap.parse_args()
    comp = args.competencia or contrato["competencia"]
    ctl = contrato["controle"]

    db = BASE / "lakehouse" / comp / "inss.duckdb"
    if not db.exists():
        print("sem Silver — rode scripts/build_silver.py primeiro")
        return 1

    t0 = time.time()
    con = duckdb.connect(str(db))

    con.execute("drop table if exists gold_concentracao_bancaria")
    con.execute("""
        create table gold_concentracao_bancaria as
        with base as (
            select
                competencia,
                banco_codigo,
                max(banco_nome)                              as banco_nome,
                uf_residencia,
                count(*)                                     as qtd_beneficios,
                sum(vl_liquido)                              as vl_total,
                round(avg(vl_liquido), 2)                    as vl_medio,
                min(vl_liquido)                              as vl_min,
                max(vl_liquido)                              as vl_max,
                banco_codigo = '998'                         as e_inss_direto
            from silver
            group by competencia, banco_codigo, uf_residencia
        ),
        por_uf as (
            select uf_residencia, sum(vl_total) as vl_uf
            from base group by uf_residencia
        )
        select
            b.competencia,
            b.banco_codigo,
            b.banco_nome,
            b.uf_residencia,
            b.qtd_beneficios,
            b.vl_total,
            b.vl_medio,
            b.vl_min,
            b.vl_max,
            b.e_inss_direto,
            round(100.0 * b.vl_total / u.vl_uf, 4)           as pct_da_uf,
            case when b.e_inss_direto then null
                 else rank() over (partition by b.uf_residencia
                                   order by b.vl_total desc)
            end                                              as posicao_na_uf
        from base b
        join por_uf u using (uf_residencia)
        order by b.uf_residencia, b.vl_total desc
    """)

    q = lambda s: con.execute(s).fetchone()[0]
    linhas = q("select count(*) from gold_concentracao_bancaria")
    soma_gold = q("select sum(vl_total) from gold_concentracao_bancaria")
    soma_silver = q("select sum(vl_liquido) from silver")
    qtd_gold = q("select sum(qtd_beneficios) from gold_concentracao_bancaria")
    qtd_silver = q("select count(*) from silver")
    ufs = q("select count(distinct uf_residencia) from gold_concentracao_bancaria")
    dup = q("""select count(*) from (
                 select competencia, banco_codigo, uf_residencia
                 from gold_concentracao_bancaria
                 group by 1,2,3 having count(*) > 1)""")
    inss_direto = q("select count(*) from gold_concentracao_bancaria where e_inss_direto")
    inss_ranqueado = q("""select count(*) from gold_concentracao_bancaria
                          where e_inss_direto and posicao_na_uf is not null""")

    # A coerência com a camada anterior vale SEMPRE. Os totais absolutos do
    # contrato valem só para a competência que ele declara.
    confere_contrato = comp == contrato["competencia"]

    falhas = []
    if soma_gold != soma_silver:
        falhas.append(f"soma gold {soma_gold} != silver {soma_silver}")
    if qtd_gold != qtd_silver:
        falhas.append(f"qtd gold {qtd_gold} != silver {qtd_silver}")
    if confere_contrato:
        if str(soma_gold) != ctl["sum_vl_liquido"]:
            falhas.append(f"soma gold {soma_gold} != contrato {ctl['sum_vl_liquido']}")
        if ufs != ctl["ufs_distintas"]:
            falhas.append(f"UFs {ufs} != contrato {ctl['ufs_distintas']}")
    elif ufs < 27:
        # cobertura nacional é estrutural, não depende da competência
        falhas.append(f"UFs {ufs} < 27 — cobertura nacional incompleta")
    if dup:
        falhas.append(f"grão duplicado em {dup} combinações")
    if not inss_direto:
        falhas.append("banco 998 ausente — deveria ter linha própria")
    if inss_ranqueado:
        falhas.append(f"banco 998 ranqueado em {inss_ranqueado} UFs — contrato proíbe")

    segundos = round(time.time() - t0)

    if falhas:
        con.execute("drop table if exists gold_concentracao_bancaria")
        con.close()
        pacote = {"status": "REJEITADO", "classificacao": "MODERN_DEFECT",
                  "falhas": falhas, "publicado": False}
        (BASE / "evidence" / f"gold-{comp.replace(chr(45), "")}.json").write_text(
            json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")
        print("\nGOLD REJEITADO — tabela removida, nada publicado")
        for f in falhas:
            print(f"  - {f}")
        return 1

    con.close()

    pacote = {
        "status": "ACEITO",
        "publicado": True,
        "competencia": comp,
        "gerado_em": datetime.now(UTC).isoformat(),
        "tabela": "gold_concentracao_bancaria",
        "grao": ["competencia", "banco_codigo", "uf_residencia"],
        "linhas": linhas,
        "qtd_beneficios": qtd_gold,
        "sum_vl_total": str(soma_gold),
        "gates": {
            "soma_confere_silver": True,
            "soma_confere_contrato": confere_contrato,
            "qtd_confere_silver": True,
            "ufs_completas": ufs,
            "grao_unico": True,
            "inss_direto_separado": inss_direto,
            "inss_direto_fora_do_ranking": True,
        },
        "segundos": segundos,
    }
    (BASE / "evidence" / f"gold-{comp.replace(chr(45), "")}.json").write_text(
        json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nGOLD ACEITO · {linhas:,} linhas de agregado · {segundos}s")
    print(f"  benefícios : {qtd_gold:,}  (confere com Silver)")
    print(f"  soma       : {soma_gold}  (confere com contrato)")
    print(f"  UFs        : {ufs}")
    print(f"  INSS-direto: {inss_direto} linhas, fora do ranking")
    return 0


if __name__ == "__main__":
    sys.exit(main())
