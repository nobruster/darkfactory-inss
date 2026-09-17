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

    t0 = time.monotonic()
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
                -- avg() sobre DECIMAL retorna DOUBLE no DuckDB. Sem o cast,
                -- vl_medio seria publicado como float — violando o ADR 0002
                -- num campo monetário do Gold. Auditoria de 16/09/2026.
                cast(round(avg(vl_liquido), 2) as decimal(18,2))
                                                             as vl_medio,
                min(vl_liquido)                              as vl_min,
                max(vl_liquido)                              as vl_max,
                -- Sentinelas: códigos que ocupam a posição de banco mas não
                -- são instituição financeira. 998 = INSS pagando direto;
                -- 996 = Acordos Internacionais (20.554 benefícios em 2026-03,
                -- ranqueado na posição 19 antes desta correção).
                -- O ADR 0005 raciocina por CLASSE, não por código único —
                -- a implementação anterior tinha só o 998. Auditoria 16/09/2026.
                banco_codigo in ('996', '998')               as e_inss_direto
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
    # ADR 0002 — toda coluna monetária é DECIMAL. Sem este gate, um avg() ou
    # uma divisão transforma dinheiro em float sem que nada acuse: a soma
    # continua batendo, porque o defeito está no TIPO, não no valor.
    monetarias_float = [
        r[0] for r in con.execute("""
            select column_name, data_type
            from information_schema.columns
            where table_name = 'gold_concentracao_bancaria'
              and column_name like 'vl_%'
              and data_type not like 'DECIMAL%'
        """).fetchall()
    ]

    # A coerência com a camada anterior vale SEMPRE. A âncora de total vale
    # sempre que existir para a competência — ver objeção #28 da auditoria.
    ancoras = contrato.get("controle_por_competencia") or {}
    ancora = ancoras.get(comp)
    if ancora is None and comp == contrato["competencia"]:
        ancora = ctl
    confere_contrato = comp == contrato["competencia"]

    falhas = []
    if soma_gold != soma_silver:
        falhas.append(f"soma gold {soma_gold} != silver {soma_silver}")
    if qtd_gold != qtd_silver:
        falhas.append(f"qtd gold {qtd_gold} != silver {qtd_silver}")
    if ancora:
        # O Gold é a camada publicada: o dinheiro que sai daqui tem de bater
        # com o que foi medido na fonte, não só com a camada de cima.
        if str(soma_gold) != ancora["sum_vl_liquido"]:
            falhas.append(f"soma gold {soma_gold} != âncora {ancora['sum_vl_liquido']}")
        if qtd_gold != ancora["count_linhas"]:
            falhas.append(f"qtd gold {qtd_gold} != âncora {ancora['count_linhas']}")
    if confere_contrato:
        if ufs != ctl["ufs_distintas"]:
            falhas.append(f"UFs {ufs} != contrato {ctl['ufs_distintas']}")
    elif ufs < 27:
        # cobertura nacional é estrutural, não depende da competência
        falhas.append(f"UFs {ufs} < 27 — cobertura nacional incompleta")
    if dup:
        falhas.append(f"grão duplicado em {dup} combinações")
    if not inss_direto:
        falhas.append("sentinela (996/998) ausente — deveria ter linha própria")
    # Fusão silenciosa de banco: dois códigos distintos com o mesmo nome
    # truncado (756/748 Sicoob-Sicredi, 037/047 Banco do Estado). O Gold agrega
    # por código, então isto não corrompe — mas se alguém trocar para nome,
    # este gate acusa. DF-INSS-002 estendido na auditoria de 16/09/2026.
    bancos_cod = q("select count(distinct banco_codigo) from gold_concentracao_bancaria")
    bancos_nome = q("select count(distinct banco_nome) from gold_concentracao_bancaria")
    if bancos_cod <= bancos_nome:
        falhas.append(
            f"agregação por nome? códigos {bancos_cod} <= nomes {bancos_nome} "
            f"(DF-INSS-002: 756/748 e 037/047 colidem)"
        )
    if inss_ranqueado:
        falhas.append(f"banco 998 ranqueado em {inss_ranqueado} UFs — contrato proíbe")
    if monetarias_float:
        falhas.append(f"coluna monetária não-DECIMAL: {monetarias_float} (ADR 0002)")

    segundos = round(time.monotonic() - t0)

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
        "status": "ACEITO" if ancora else "ACEITO_SEM_ANCORA",
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
            "soma_confere_ancora": bool(ancora),
            "qtd_confere_ancora": bool(ancora),
            "soma_confere_contrato": confere_contrato,
            "qtd_confere_silver": True,
            "monetarias_sao_decimal": True,
            "sem_fusao_por_nome": True,
            "ufs_completas": ufs,
            "grao_unico": True,
            "inss_direto_separado": inss_direto,
            "inss_direto_fora_do_ranking": True,
        },
        "segundos": segundos,
    }
    (BASE / "evidence" / f"gold-{comp.replace(chr(45), "")}.json").write_text(
        json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nGOLD {pacote['status']} · {linhas:,} linhas de agregado · {segundos}s")
    print(f"  benefícios : {qtd_gold:,}  (confere com Silver)")
    print(f"  soma       : {soma_gold}  "
          f"{"(confere com a âncora da fonte)" if ancora else "(SEM ÂNCORA)"}")
    print(f"  UFs        : {ufs}")
    print(f"  INSS-direto: {inss_direto} linhas, fora do ranking")
    return 0


if __name__ == "__main__":
    sys.exit(main())
