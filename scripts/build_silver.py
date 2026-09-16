#!/usr/bin/env python3
"""Silver — grão conformado a partir do Bronze.

Contrato (contracts/layout.yaml):
  - vl_liquido vira DECIMAL(18,2). Nunca float.
  - dt_credito vira DATE (ISO-8601).
  - trim em todo texto; banco e município separados em código + nome.
  - especie_nome vem do dicionário OFICIAL (join pelo código, nunca pelo nome).
  - especie_nome_fonte preserva o nome do SUIBE — DF-INSS-004 não se apaga.
  - count e soma devem bater com o Bronze. Tolerância ZERO.

Não lê a fonte legada. Reconstrói só a partir do landing.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import yaml

BASE = Path("/home/nobru/darkfactory-inss")


def main() -> int:
    contrato = yaml.safe_load((BASE / "contracts" / "layout.yaml").read_text(encoding="utf-8"))
    comp = contrato["competencia"]
    especies = json.loads((BASE / "contracts" / "_especies.json").read_text(encoding="utf-8"))

    bronze = BASE / "landing" / comp / "bronze.parquet"
    if not bronze.exists():
        print("sem Bronze — rode ingestion/ingest_bronze.py primeiro")
        return 1

    destino = BASE / "lakehouse" / comp
    parcial = BASE / "lakehouse" / f".{comp}.parcial"
    shutil.rmtree(parcial, ignore_errors=True)
    parcial.mkdir(parents=True)

    t0 = time.time()
    con = duckdb.connect(str(parcial / "inss.duckdb"))

    # dicionário oficial como tabela — o join é pelo CÓDIGO
    con.execute("create table dic_especie (codigo varchar primary key, nome varchar)")
    con.executemany(
        "insert into dic_especie values (?, ?)", sorted(especies.items())
    )

    # os 34 códigos cujo nome colide após truncamento (DF-INSS-002)
    colisoes = contrato["defeitos_fonte"][1]["colisoes_especie"]
    colidentes = sorted({c for v in colisoes.values() for c in v})
    lista = ", ".join(f"'{c}'" for c in colidentes)

    con.execute(f"""
        create table silver as
        select
            trim(b.despacho)                                   as despacho,
            trim(b.sexo)                                       as sexo,
            trim(b.clientela)                                  as clientela,
            trim(b.tipo_beneficio)                             as tipo_beneficio,
            trim(b.uf_residencia)                              as uf_residencia,
            trim(b.meio_pagamento)                             as meio_pagamento,

            split_part(trim(b.banco), '-', 1)                  as banco_codigo,
            trim(substr(trim(b.banco),
                 position('-' in trim(b.banco)) + 1))          as banco_nome,

            split_part(trim(b.mun_pagto), '-', 1)              as mun_pagto_codigo,
            split_part(trim(b.mun_residencia), '-', 1)         as mun_residencia_codigo,

            cast(replace(replace(trim(b.vl_liquido), '.', ''), ',', '.')
                 as decimal(18,2))                             as vl_liquido,

            trim(b.ramo_atividade)                             as ramo_atividade,
            strptime(trim(b.dt_credito), '%d/%m/%Y')::date     as dt_credito,

            lpad(trim(b.especie_codigo), 2, '0')               as especie_codigo,
            d.nome                                             as especie_nome,
            trim(b.especie_nome_truncado)                      as especie_nome_fonte,
            lpad(trim(b.especie_codigo), 2, '0')
                || ' · ' || d.nome                             as especie_rotulo,
            (trim(b.especie_nome_truncado) = substr(d.nome, 1, 20))
                                                               as especie_nome_confere,
            lpad(trim(b.especie_codigo), 2, '0') in ({lista})  as especie_colide,

            '{comp}'                                           as competencia,
            b._linha_origem
        from read_parquet('{bronze}') b
        left join dic_especie d
               on d.codigo = lpad(trim(b.especie_codigo), 2, '0')
    """)

    # ── gates ────────────────────────────────────────────────────────────
    q = lambda s: con.execute(s).fetchone()[0]
    n_silver = q("select count(*) from silver")
    soma_silver = q("select sum(vl_liquido) from silver")
    n_bronze = q(f"select count(*) from read_parquet('{bronze}')")
    soma_bronze = q(f"""select sum(cast(replace(replace(trim(vl_liquido),'.',''),',','.')
                        as decimal(18,2))) from read_parquet('{bronze}')""")
    nulos = q("select count(*) from silver where especie_nome is null")
    rotulos = q("select count(distinct especie_rotulo) from silver")
    divergentes = q("select count(distinct especie_codigo) from silver where not especie_nome_confere")
    datas_nulas = q("select count(*) from silver where dt_credito is null")

    falhas = []
    if n_silver != n_bronze:
        falhas.append(f"count silver {n_silver} != bronze {n_bronze}")
    if soma_silver != soma_bronze:
        falhas.append(f"soma silver {soma_silver} != bronze {soma_bronze}")
    if nulos:
        falhas.append(f"especie_nome nulo em {nulos} linhas — join quebrado")
    if rotulos != 65:
        falhas.append(f"especie_rotulo distintos {rotulos} != 65")
    if divergentes != 29:
        falhas.append(f"divergentes {divergentes} != 29 (DF-INSS-004)")
    if datas_nulas:
        falhas.append(f"dt_credito nula em {datas_nulas} linhas")

    con.close()
    segundos = round(time.time() - t0)

    if falhas:
        shutil.rmtree(parcial, ignore_errors=True)
        pacote = {"status": "REJEITADO", "classificacao": "MODERN_DEFECT",
                  "falhas": falhas, "publicado": False}
        (BASE / "evidence" / "silver-run.json").write_text(
            json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")
        print("\nSILVER REJEITADO — nada publicado")
        for f in falhas:
            print(f"  - {f}")
        return 1

    shutil.rmtree(destino, ignore_errors=True)
    parcial.rename(destino)

    pacote = {
        "status": "ACEITO",
        "publicado": True,
        "competencia": comp,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "linhas": n_silver,
        "sum_vl_liquido": str(soma_silver),
        "gates": {
            "count_confere_bronze": True,
            "soma_confere_bronze": True,
            "especie_nome_sem_nulo": True,
            "rotulos_distintos": rotulos,
            "dt_credito_sem_nulo": True,
        },
        "DF-INSS-004": {
            "codigos_divergentes": divergentes,
            "classificacao": "CONTRACT_AMBIGUITY",
            "nota": "fonte e dicionário usam nomenclaturas diferentes; ambos preservados",
        },
        "segundos": segundos,
    }
    (BASE / "evidence" / "silver-run.json").write_text(
        json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nSILVER ACEITO · {n_silver:,} linhas · {segundos}s")
    print(f"  soma            : {soma_silver}  (confere com Bronze)")
    print(f"  rótulos únicos  : {rotulos}")
    print(f"  DF-INSS-004     : {divergentes} códigos divergentes (preservados)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
