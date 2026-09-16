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

    # dicionário oficial como tabela — o join é pelo CÓDIGO.
    # `origem` distingue o que o INSS publica do que apenas observamos:
    # nenhum relatório deve apresentar nome observado como se fosse oficial.
    con.execute("""create table dic_especie
                   (codigo varchar primary key, nome varchar, origem varchar)""")
    con.executemany("insert into dic_especie values (?, ?, 'dicionario_oficial')",
                    sorted(especies.items()))

    # complemento: códigos na fonte e ausentes do oficial (DF-INSS-003)
    compl_path = BASE / "contracts" / "especies-complemento.yaml"
    if compl_path.exists():
        compl = yaml.safe_load(compl_path.read_text(encoding="utf-8"))
        for cod, d in (compl.get("especies") or {}).items():
            if cod not in especies:   # o oficial sempre vence
                con.execute("insert into dic_especie values (?, ?, ?)",
                            [cod, d["nome"], d.get("origem", "fonte")])

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

            -- O código SUIBE de 5 dígitos É único: 5.572 códigos ↔ 5.572 nomes,
            -- zero colisão nos dois sentidos (medido em 2026-03). É chave legítima.
            --
            -- ⚠ O que NÃO se pode fazer é confundi-lo com uf_residencia. A UF
            -- embutida no nome ('21504-Sp-São Paulo') é a UF do MUNICÍPIO; a
            -- coluna uf_residencia é a UF do BENEFICIÁRIO. Elas divergem em
            -- 429.803 linhas de uma amostra de 7 UFs — são dois fatos distintos.
            -- Agrupar por (uf_residencia, codigo) partiria São Paulo em 27
            -- pedaços. Ver DF-INSS-005. Auditoria 16/09/2026, objeção #4.
            split_part(trim(b.mun_pagto), '-', 1)              as mun_pagto_codigo,
            split_part(trim(b.mun_residencia), '-', 1)         as mun_residencia_codigo,
            split_part(trim(b.mun_residencia), '-', 2)         as mun_residencia_uf,
            trim(b.mun_residencia)                             as mun_residencia_fonte,

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
            -- Órfão = ausente do dicionário OFICIAL do INSS. O complemento dá
            -- rótulo legível, mas NÃO apaga a marca: o contrato manda
            -- "especie_orfa = true marca a linha" (DF-INSS-003), e a
            -- ambiguidade continua aberta enquanto o INSS não documentar.
            -- Antes desta correção, o complemento zerava a flag — auditoria 16/09/2026.
            (d.origem is null or d.origem <> 'dicionario_oficial')
                                                               as especie_orfa,
            coalesce(d.origem, 'ausente')                      as especie_nome_origem,

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
    do_complemento = [r[0] for r in con.execute(
        "select distinct especie_codigo from silver where especie_nome_origem = 'fonte' order by 1"
    ).fetchall()]

    falhas = []
    if n_silver != n_bronze:
        falhas.append(f"count silver {n_silver} != bronze {n_bronze}")
    if soma_silver != soma_bronze:
        falhas.append(f"soma silver {soma_silver} != bronze {soma_bronze}")
    # o complemento NUNCA sobrepõe o oficial: se um código tem nome do INSS,
    # é esse que vale. Sobreposição silenciosa reescreveria o juiz.
    sobreposto = [c for c in do_complemento if c in especies]
    if sobreposto:
        falhas.append(f"complemento sobrepôs o dicionário oficial em {sobreposto}")
    # DF-INSS-003: código na fonte, ausente do dicionário oficial.
    # NÃO é join quebrado — o join funcionou e não achou. É CONTRACT_AMBIGUITY:
    # classifica-se e escala, sem inventar descrição e sem falhar a execução.
    orfaos = [r[0] for r in con.execute(
        "select distinct especie_codigo from silver where especie_orfa order by 1"
    ).fetchall()] if nulos else []
    # Os números de espécie do contrato valem para a competência que ele declara.
    # Em outra competência viram observação medida, não gate — a fonte muda.
    # Mas a ÂNCORA de total vale sempre que existir: ver objeção #28.
    ancoras = contrato.get("controle_por_competencia") or {}
    ancora = ancoras.get(comp)
    if ancora is None and comp == contrato["competencia"]:
        ancora = contrato["controle"]
    if ancora:
        if n_silver != ancora["count_linhas"]:
            falhas.append(f"count silver {n_silver} != âncora {ancora['count_linhas']}")
        if str(soma_silver) != ancora["sum_vl_liquido"]:
            falhas.append(f"soma silver {soma_silver} != âncora {ancora['sum_vl_liquido']}")
    confere_contrato = comp == contrato["competencia"]
    if confere_contrato:
        if rotulos != 65:
            falhas.append(f"especie_rotulo distintos {rotulos} != 65")
        if divergentes != 29:
            falhas.append(f"divergentes {divergentes} != 29 (DF-INSS-004)")
    if datas_nulas:
        falhas.append(f"dt_credito nula em {datas_nulas} linhas")
    # DF-INSS-005 — o código de município só é chave enquanto for bijetivo com
    # o nome. Se o INSS reciclar um código, agregações por município passam a
    # somar cidades diferentes e o total continua batendo. Este gate é o único
    # lugar onde isso apareceria.
    mun_ambiguo = q("""select count(*) from (
                         select mun_residencia_codigo from silver
                         group by 1 having count(distinct mun_residencia_fonte) > 1)""")
    if mun_ambiguo:
        falhas.append(f"mun_residencia_codigo com >1 nome em {mun_ambiguo} códigos "
                      f"(DF-INSS-005: deixou de ser chave)")

    con.close()
    segundos = round(time.time() - t0)

    if falhas:
        shutil.rmtree(parcial, ignore_errors=True)
        pacote = {"status": "REJEITADO", "classificacao": "MODERN_DEFECT",
                  "falhas": falhas, "publicado": False}
        (BASE / "evidence" / f"silver-{comp.replace(chr(45), "")}.json").write_text(
            json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")
        print("\nSILVER REJEITADO — nada publicado")
        for f in falhas:
            print(f"  - {f}")
        return 1

    shutil.rmtree(destino, ignore_errors=True)
    parcial.rename(destino)

    pacote = {
        "status": "ACEITO" if ancora else "ACEITO_SEM_ANCORA",
        "publicado": True,
        "competencia": comp,
        "gerado_em": datetime.now(UTC).isoformat(),
        "linhas": n_silver,
        "sum_vl_liquido": str(soma_silver),
        "gates": {
            "count_confere_bronze": True,
            "soma_confere_bronze": True,
            "count_confere_ancora": bool(ancora),
            "soma_confere_ancora": bool(ancora),
            "rotulos_distintos": rotulos,
            "dt_credito_sem_nulo": True,
            "municipio_codigo_e_chave": True,
            "numeros_do_contrato_conferidos": confere_contrato,
        },
        "DF-INSS-003": {
            "codigos_orfaos": orfaos,
            "codigos_do_complemento": do_complemento,
            "linhas_afetadas": nulos,
            "classificacao": "CONTRACT_AMBIGUITY" if orfaos else None,
            "nota": ("código presente na fonte e ausente do dicionário oficial; "
                     "especie_nome fica nulo, especie_nome_fonte preserva a origem, "
                     "especie_orfa marca a linha. NÃO se inventa descrição.")
            if orfaos else "sem órfãos nesta competência",
        },
        "DF-INSS-004": {
            "codigos_divergentes": divergentes,
            "classificacao": "CONTRACT_AMBIGUITY",
            "nota": "fonte e dicionário usam nomenclaturas diferentes; ambos preservados",
        },
        "segundos": segundos,
    }
    (BASE / "evidence" / f"silver-{comp.replace(chr(45), "")}.json").write_text(
        json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nSILVER {pacote['status']} · {n_silver:,} linhas · {segundos}s")
    print(f"  soma            : {soma_silver}  "
          f"{"(confere com Bronze e âncora)" if ancora else "(confere com Bronze; SEM ÂNCORA)"}")
    print(f"  rótulos únicos  : {rotulos}")
    print(f"  DF-INSS-004     : {divergentes} divergências de nomenclatura")
    if orfaos:
        print(f"  DF-INSS-003     : órfãos {orfaos} · {nulos} linhas · CONTRACT_AMBIGUITY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
