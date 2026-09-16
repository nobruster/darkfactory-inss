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
from datetime import datetime, timezone
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
    contrato = carregar_contrato()
    ctl = contrato["controle"]
    ncols = contrato["fonte"]["colunas"]
    nomes = [c["nome"] for c in contrato["colunas"]]
    schema = schema_de(contrato)

    destino = BASE / "landing" / contrato["competencia"]
    parcial = BASE / "landing" / f".{contrato['competencia']}.parcial"
    if parcial.exists():
        shutil.rmtree(parcial)
    parcial.mkdir(parents=True)

    fonte = BASE / "_raw" / "fonte.zip"
    z = zipfile.ZipFile(fonte)
    membro = z.namelist()[0]

    colunas: list[list[str]] = [[] for _ in range(ncols)]
    origem: list[int] = []
    rejeicoes: list[dict] = []
    total = 0
    soma = Decimal("0")
    parte = 0
    t0 = time.time()
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
                print(f"  {total:,} linhas · {time.time() - t0:.0f}s", flush=True)

    descarregar()
    if escritor is not None:
        escritor.close()

    segundos = round(time.time() - t0)

    # ── gates do contrato ────────────────────────────────────────────────
    falhas: list[str] = []
    if rejeicoes:
        falhas.append(f"rejeicoes={len(rejeicoes)} (contrato exige 0)")
    if total != ctl["count_linhas"]:
        falhas.append(f"count {total} != contrato {ctl['count_linhas']}")
    if str(soma) != ctl["sum_vl_liquido"]:
        falhas.append(f"soma {soma} != contrato {ctl['sum_vl_liquido']}")

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
        (BASE / "evidence" / "bronze-run.json").write_text(
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

    manifesto = {
        "competencia": contrato["competencia"],
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "fonte_sha256": contrato["fonte"]["zip_sha256"],
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

    pacote = {
        "status": "ACEITO",
        "publicado": True,
        "gates": {
            "rejeicoes_zero": True,
            "count_confere": True,
            "soma_confere": True,
        },
        **manifesto,
    }
    (BASE / "evidence" / "bronze-run.json").write_text(
        json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nBRONZE ACEITO · {total:,} linhas · {segundos}s")
    print(f"  soma  : {soma}  (confere com o contrato)")
    print(f"  bytes : {arquivo.stat().st_size:,}")
    print(f"  sha256: {sha[:32]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
