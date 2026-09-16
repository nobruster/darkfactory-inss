#!/usr/bin/env python3
"""Confere um Bronze já publicado contra a âncora medida na fonte.

Por que existe
--------------
Três packets de Bronze foram publicados como ACEITO enquanto os gates de total
estavam desligados (objeção #28 da auditoria de 16/09/2026). O Parquet está
lá, o sha256 está lá — o que nunca aconteceu foi a conferência.

Editar aqueles packets para dizer o que a gente gostaria que dissessem seria
falsificar evidência. E reprocessar 41M linhas para refazer um Parquet
byte-idêntico gastaria uma hora para produzir o mesmo arquivo.

A saída honesta é a terceira: conferir o artefato publicado contra a âncora
AGORA, e gravar isso como evidência NOVA. O packet antigo continua no git
dizendo o que dizia. Este arquivo diz quando a conferência aconteceu e o que
ela achou. As duas coisas ficam no histórico — que é o ponto.

Isto NÃO substitui o gate do Bronze. É a reparação de uma dívida específica;
daqui para frente `ingest_bronze.py` confere na hora.

Uso:
  python3 scripts/ancorar_bronze.py --competencia 2026-02
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import yaml

BASE = Path(__file__).resolve().parents[1]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia", required=True)
    args = ap.parse_args()
    comp = args.competencia
    aaaamm = comp.replace("-", "")

    contrato = yaml.safe_load(
        (BASE / "contracts" / "layout.yaml").read_text(encoding="utf-8")
    )
    ancoras = contrato.get("controle_por_competencia") or {}
    ancora = ancoras.get(comp)
    if ancora is None and comp == contrato["competencia"]:
        ancora = contrato["controle"]
    if ancora is None:
        print(f"sem âncora para {comp} em controle_por_competencia.")
        print(f"  meça primeiro: python3 scripts/totais_controle.py --competencia {comp}")
        return 1

    parquet = BASE / "landing" / comp / "bronze.parquet"
    if not parquet.exists():
        print(f"sem Bronze publicado para {comp}")
        return 1

    t0 = time.time()

    # 1. o Parquet ainda é o que foi publicado?
    registro = BASE / "landing" / comp / "bronze.parquet.sha256"
    sha_atual = sha256(parquet)
    sha_publicado = registro.read_text(encoding="utf-8").split()[0] if registro.exists() else None
    intacto = sha_publicado == sha_atual

    # 2. o que está dentro dele bate com a fonte?
    con = duckdb.connect()
    q = lambda s: con.execute(s).fetchone()[0]
    p = str(parquet)
    linhas = q(f"select count(*) from read_parquet('{p}')")
    soma = q(f"""select sum(cast(replace(replace(trim(vl_liquido),'.',''),',','.')
                 as decimal(18,2))) from read_parquet('{p}')""")
    minimo = q(f"""select min(cast(replace(replace(trim(vl_liquido),'.',''),',','.')
                   as decimal(18,2))) from read_parquet('{p}')""")
    maximo = q(f"""select max(cast(replace(replace(trim(vl_liquido),'.',''),',','.')
                   as decimal(18,2))) from read_parquet('{p}')""")
    con.close()

    divergencias = []
    if not intacto:
        divergencias.append(
            f"sha256 do Parquet mudou desde a publicação: "
            f"{sha_publicado} -> {sha_atual}")
    if linhas != ancora["count_linhas"]:
        divergencias.append(f"count {linhas} != âncora {ancora['count_linhas']}")
    if str(soma) != ancora["sum_vl_liquido"]:
        divergencias.append(f"soma {soma} != âncora {ancora['sum_vl_liquido']}")
    if str(minimo) != ancora["min_vl_liquido"]:
        divergencias.append(f"mínimo {minimo} != âncora {ancora['min_vl_liquido']}")
    if str(maximo) != ancora["max_vl_liquido"]:
        divergencias.append(f"máximo {maximo} != âncora {ancora['max_vl_liquido']}")

    packet_antigo = BASE / "evidence" / f"bronze-{aaaamm}.json"
    status_antigo = None
    gates_antigos = None
    if packet_antigo.exists():
        d = json.loads(packet_antigo.read_text(encoding="utf-8"))
        status_antigo = d.get("status")
        gates_antigos = d.get("gates")

    saida = {
        "tipo": "conferencia_retroativa",
        "competencia": comp,
        "conferido_em": datetime.now(UTC).isoformat(),
        "motivo": ("packet publicado com gates de total desligados; "
                   "auditoria de 16/09/2026, objeção #28"),
        "packet_original": {
            "arquivo": f"evidence/bronze-{aaaamm}.json",
            "status": status_antigo,
            "gates": gates_antigos,
            "nota": "preservado como está — evidência não se edita",
        },
        "ancora": {
            "fonte": ancora.get("evidencia"),
            "medida_em": ancora.get("medido_em"),
            "count_linhas": ancora["count_linhas"],
            "sum_vl_liquido": ancora["sum_vl_liquido"],
        },
        "medido_no_parquet": {
            "count_linhas": linhas,
            "sum_vl_liquido": str(soma),
            "min_vl_liquido": str(minimo),
            "max_vl_liquido": str(maximo),
            "sha256": sha_atual,
            "parquet_intacto": intacto,
        },
        "resultado": "CONFERE" if not divergencias else "DIVERGE",
        "divergencias": divergencias,
        "segundos": round(time.time() - t0),
    }
    destino = BASE / "evidence" / f"bronze-{aaaamm}-conferencia.json"
    destino.write_text(json.dumps(saida, indent=2, ensure_ascii=False),
                       encoding="utf-8")

    print(f"\n{saida['resultado']} · {comp} · {saida['segundos']}s")
    print(f"  count : {linhas:,}")
    print(f"  soma  : {soma}")
    print(f"  sha256: {'intacto' if intacto else 'MUDOU'}")
    for d in divergencias:
        print(f"  - {d}")
    print(f"\n  {destino.relative_to(BASE)}")
    return 1 if divergencias else 0


if __name__ == "__main__":
    sys.exit(main())
