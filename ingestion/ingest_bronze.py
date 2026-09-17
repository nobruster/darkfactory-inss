#!/usr/bin/env python3
"""Bronze — landing Parquet a partir da fonte congelada.

Regras do contrato (contracts/layout.yaml):
  - leitura POSICIONAL (o cabeçalho tem "Espécie" duas vezes)
  - nenhuma transformação: Bronze é alinhado à fonte, texto cru
  - linha com != 14 colunas é rejeitada; rejeicoes > 0 FALHA a execução
  - ZERO Parquet parcial: só publica se tudo passar
  - totais de controle conferidos contra o contrato

Não lê PostgreSQL, não consulta a fonte legada, não inventa valor.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import time
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

BASE = Path("/home/nobru/darkfactory-inss")
LOTE = 2_000_000  # linhas por bloco escrito


def carregar_contrato() -> dict:
    return yaml.safe_load((BASE / "contracts" / "layout.yaml").read_text(encoding="utf-8"))


def schema_de(contrato: dict) -> pa.Schema:
    """Bronze é texto cru: toda coluna string, exatamente como veio."""
    campos = [pa.field(c["nome"], pa.string()) for c in contrato["colunas"]]
    campos.append(pa.field("_linha_origem", pa.int64()))
    return pa.schema(campos)


def sha256_de(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="fonte -> landing Parquet")
    ap.add_argument("--competencia", help="AAAA-MM; padrão: a do contrato")
    args = ap.parse_args()

    contrato = carregar_contrato()
    comp = args.competencia or contrato["competencia"]
    aaaamm = comp.replace("-", "")
    # A âncora é POR COMPETÊNCIA. O bloco `controle:` legado vale para a
    # competência que o contrato declara; `controle_por_competencia:` cobre
    # as demais, com números medidos direto do ZIP por totais_controle.py.
    #
    # Sem âncora não existe gate de total — e isso não pode passar por ACEITO
    # normal. Ver objeção #28 da auditoria de 16/09/2026.
    ancoras = contrato.get("controle_por_competencia") or {}
    ctl = ancoras.get(comp)
    if ctl is None and comp == contrato["competencia"]:
        ctl = contrato["controle"]
    confere_controle = ctl is not None
    ncols = contrato["fonte"]["colunas"]
    nomes = [c["nome"] for c in contrato["colunas"]]
    schema = schema_de(contrato)

    destino = BASE / "landing" / comp
    parcial = BASE / "landing" / f".{comp}.parcial"
    if parcial.exists():
        shutil.rmtree(parcial)
    parcial.mkdir(parents=True)

    fonte = BASE / "_raw" / f"fonte-{aaaamm}.zip"
    if not fonte.exists():
        print(f"sem fonte para {comp}. rode antes:")
        print(f"  python3 ingestion/fetch_fonte.py --competencia {comp}")
        return 1
    z = zipfile.ZipFile(fonte)
    membro = z.namelist()[0]

    colunas: list[list[str]] = [[] for _ in range(ncols)]
    origem: list[int] = []
    rejeicoes: list[dict] = []
    total = 0
    soma = Decimal("0")
    parte = 0
    t0 = time.monotonic()
    escritor = None

    def descarregar() -> None:
        nonlocal escritor, parte, colunas, origem
        if not origem:
            return
        arrays = [pa.array(col, type=pa.string()) for col in colunas]
        arrays.append(pa.array(origem, type=pa.int64()))
        tabela = pa.Table.from_arrays(arrays, schema=schema)
        if escritor is None:
            escritor = pq.ParquetWriter(
                parcial / "bronze.parquet", schema, compression="zstd"
            )
        escritor.write_table(tabela)
        parte += 1
        colunas = [[] for _ in range(ncols)]
        origem = []

    with z.open(membro) as f:
        texto = io.TextIOWrapper(f, encoding=contrato["fonte"]["encoding"])
        texto.readline()  # descarta o cabeçalho ambíguo — lemos por posição
        for n, linha in enumerate(texto, start=2):
            partes = linha.rstrip("\r\n").split(";")
            if len(partes) != ncols:
                rejeicoes.append(
                    {"linha": n, "motivo": "contagem_de_colunas", "colunas": len(partes)}
                )
                continue
            for i in range(ncols):
                colunas[i].append(partes[i])
            origem.append(n)
            total += 1
            try:
                soma += Decimal(partes[9].strip().replace(".", "").replace(",", "."))
            except Exception:
                rejeicoes.append({"linha": n, "motivo": "vl_liquido_ilegivel"})
            if total % LOTE == 0:
                descarregar()
                print(f"  {total:,} linhas · {time.monotonic() - t0:.0f}s", flush=True)

    descarregar()
    if escritor is not None:
        escritor.close()

    segundos = round(time.monotonic() - t0)

    # ── gates do contrato ────────────────────────────────────────────────
    # A estrutura (14 colunas, zero rejeição) vale para TODA competência.
    # Os totais de controle valem só para a que o contrato declara — uma
    # competência nova tem outros números, e isso não é defeito.
    falhas: list[str] = []
    if rejeicoes:
        falhas.append(f"rejeicoes={len(rejeicoes)} (contrato exige 0)")
    if confere_controle:
        if total != ctl["count_linhas"]:
            falhas.append(f"count {total} != contrato {ctl['count_linhas']}")
        if str(soma) != ctl["sum_vl_liquido"]:
            falhas.append(f"soma {soma} != contrato {ctl['sum_vl_liquido']}")
    else:
        print(f"\n  ⚠ SEM ÂNCORA para {comp} — nenhum gate de total rodou.")
        print("  Medidos aqui (não conferidos contra nada):")
        print(f"    count = {total:,}")
        print(f"    soma  = {soma}")
        print("\n  Para ancorar esta competência, meça a fonte de forma")
        print("  independente e registre em controle_por_competencia:")
        print(f"    python3 scripts/totais_controle.py --competencia {comp}")

    if falhas:
        # ZERO Parquet: nada é publicado quando um gate reprova
        shutil.rmtree(parcial, ignore_errors=True)
        pacote = {
            "status": "REJEITADO",
            "classificacao": "MODERN_DEFECT",
            "falhas": falhas,
            "rejeicoes": rejeicoes[:100],
            "publicado": False,
        }
        (BASE / "evidence" / f"bronze-{aaaamm}.json").write_text(
            json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("\nBRONZE REJEITADO — nenhum Parquet publicado")
        for f_ in falhas:
            print(f"  - {f_}")
        return 1

    # ── publicação atômica: só agora o destino passa a existir ───────────
    if destino.exists():
        shutil.rmtree(destino)
    parcial.rename(destino)

    arquivo = destino / "bronze.parquet"
    sha = sha256_de(arquivo)
    (destino / "bronze.parquet.sha256").write_text(
        f"{sha}  bronze.parquet\n", encoding="utf-8"
    )

    sha_fonte = (BASE / "_raw" / f"fonte-{aaaamm}.zip.sha256")
    manifesto = {
        "competencia": comp,
        "gerado_em": datetime.now(UTC).isoformat(),
        "fonte_sha256": (sha_fonte.read_text(encoding="utf-8").split()[0]
                         if sha_fonte.exists() else None),
        "parquet_sha256": sha,
        "parquet_bytes": arquivo.stat().st_size,
        "linhas": total,
        "sum_vl_liquido": str(soma),
        "colunas": nomes,
        "blocos": parte,
        "segundos": segundos,
        "contrato_versao": contrato["version"],
    }
    (destino / "parquet-manifest.json").write_text(
        json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Um packet que diz ACEITO com "count_confere": false lá dentro mente por
    # omissão: quem lê o status não vê que o gate nem rodou. O estado passa a
    # ser explícito. Auditoria de 16/09/2026, objeção #28.
    pacote = {
        "status": "ACEITO" if confere_controle else "ACEITO_SEM_ANCORA",
        "publicado": True,
        "ancora": ctl["evidencia"] if confere_controle and "evidencia" in ctl
                  else ("contracts/layout.yaml:controle" if confere_controle else None),
        "gates": {
            "rejeicoes_zero": True,
            "count_confere": confere_controle,
            "soma_confere": confere_controle,
        },
        **manifesto,
    }
    if not confere_controle:
        pacote["aviso"] = (
            f"Sem âncora medida para {comp}: os totais NÃO foram conferidos "
            f"contra a fonte. Rode scripts/totais_controle.py --competencia "
            f"{comp} e registre em controle_por_competencia."
        )
    (BASE / "evidence" / f"bronze-{aaaamm}.json").write_text(
        json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nBRONZE {pacote['status']} · {total:,} linhas · {segundos}s")
    print(f"  soma  : {soma}  {"(confere com a âncora)" if confere_controle else "(SEM ÂNCORA — não conferido)"}")
    print(f"  bytes : {arquivo.stat().st_size:,}")
    print(f"  sha256: {sha[:32]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
