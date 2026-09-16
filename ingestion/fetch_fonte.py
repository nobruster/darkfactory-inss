#!/usr/bin/env python3
"""Fetch — baixa a fonte de uma competência e a congela.

Etapa 0 do pipeline. Produz:
  _raw/fonte-<AAAAMM>.zip            somente-leitura (chmod 444)
  _raw/fonte-<AAAAMM>.zip.sha256     a cadeia de custódia começa aqui
  evidence/fetch-<AAAAMM>.json       packet com os gates

Gates:
  - HTTP 200 e Content-Length declarado
  - bytes recebidos == Content-Length
  - o ZIP abre e tem exatamente 1 membro
  - se o arquivo já existe, o sha256 precisa bater (idempotência)

Uso:
  python3 ingestion/fetch_fonte.py --competencia 2026-02
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
URL_TEMPLATE = (
    "https://armazenamento-dadosabertos.s3.sa-east-1.amazonaws.com/"
    "PDA_2025_2027/Grupos_de_dados/Benef%C3%ADcios+emitidos/"
    "D.SDA.PDA.003.EMI.{aaaamm}.CSV.ZIP"
)


def sha256_de(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="baixa e congela a fonte de uma competência")
    ap.add_argument("--competencia", required=True, help="AAAA-MM, ex: 2026-02")
    ap.add_argument("--force", action="store_true",
                    help="rebaixa mesmo já existindo (reprocessamento deliberado)")
    ap.add_argument("--check-remoto", action="store_true",
                    help="consulta o servidor para ver se a fonte mudou, sem baixar")
    args = ap.parse_args()

    comp = args.competencia
    aaaamm = comp.replace("-", "")
    url = URL_TEMPLATE.format(aaaamm=aaaamm)

    raw = BASE / "_raw"
    raw.mkdir(exist_ok=True)
    destino = raw / f"fonte-{aaaamm}.zip"
    parcial = raw / f".fonte-{aaaamm}.parcial"

    t0 = time.time()
    falhas: list[str] = []

    # ── NUNCA rebaixar o que já está no disco ────────────────────────────
    # Rebaixar 575 MB é desperdício e, pior, arrisca trocar a fonte por baixo
    # de evidências já emitidas. Só acontece com --force explícito.
    if destino.exists() and not args.force:
        sha_atual = sha256_de(destino)
        arquivo_sha = raw / f"fonte-{aaaamm}.zip.sha256"
        if arquivo_sha.exists():
            sha_gravado = arquivo_sha.read_text(encoding="utf-8").split()[0]
            if sha_atual != sha_gravado:
                print(f"FONTE ALTERADA NO DISCO — sha {sha_atual[:16]}… "
                      f"!= registrado {sha_gravado[:16]}…")
                print("investigue antes de prosseguir; não rebaixe por reflexo")
                return 1

        # opcional: pergunta ao servidor se a fonte mudou, sem baixar o corpo
        if args.check_remoto:
            try:
                req = urllib.request.Request(
                    url, method="HEAD",
                    headers={"User-Agent": "darkfactory-inss/1.0"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    remoto = int(r.headers.get("Content-Length", 0))
                    modificado = r.headers.get("Last-Modified", "?")
                local = destino.stat().st_size
                if remoto and remoto != local:
                    print(f"⚠ REMOTO MUDOU · {local:,} -> {remoto:,} bytes "
                          f"(Last-Modified {modificado})")
                    print("  use --force para rebaixar deliberadamente")
                    return 2
                print(f"remoto inalterado ({remoto:,} bytes · {modificado})")
            except Exception as e:
                print(f"não deu para checar o remoto: {e}")

        print(f"já baixada · {destino.stat().st_size:,} bytes · sha {sha_atual[:16]}…")
        print("nada a fazer — use --force se quiser rebaixar")
        return 0

    if destino.exists() and args.force:
        print(f"--force: rebaixando {comp} apesar de já existir")
        os.chmod(destino, 0o644)  # destravar para poder substituir

    print(f"baixando {comp} …")
    req = urllib.request.Request(url, headers={"User-Agent": "darkfactory-inss/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        if resp.status != 200:
            print(f"HTTP {resp.status}")
            return 1
        declarado = int(resp.headers.get("Content-Length", 0))
        recebido = 0
        with parcial.open("wb") as f:
            while bloco := resp.read(1 << 20):
                f.write(bloco)
                recebido += len(bloco)
                if recebido % (50 << 20) < (1 << 20):
                    pct = 100 * recebido / declarado if declarado else 0
                    print(f"  {recebido // (1 << 20):,} MB · {pct:.0f}%", flush=True)

    # ── gates ────────────────────────────────────────────────────────────
    if declarado and recebido != declarado:
        falhas.append(f"bytes {recebido} != Content-Length {declarado}")
    try:
        z = zipfile.ZipFile(parcial)
        membros = z.namelist()
        if len(membros) != 1:
            falhas.append(f"ZIP tem {len(membros)} membros, esperado 1")
        csv_bytes = z.getinfo(membros[0]).file_size if membros else 0
        z.close()
    except zipfile.BadZipFile as e:
        falhas.append(f"ZIP inválido: {e}")
        membros, csv_bytes = [], 0

    if falhas:
        parcial.unlink(missing_ok=True)
        pacote = {"status": "REJEITADO", "competencia": comp,
                  "classificacao": "MODERN_DEFECT", "falhas": falhas,
                  "publicado": False}
        (BASE / "evidence" / f"fetch-{aaaamm}.json").write_text(
            json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")
        print("\nFETCH REJEITADO — nada congelado")
        for f_ in falhas:
            print(f"  - {f_}")
        return 1

    # ── publicação: só agora vira arquivo oficial ────────────────────────
    parcial.rename(destino)
    sha = sha256_de(destino)
    registro = raw / f"fonte-{aaaamm}.zip.sha256"
    if registro.exists():
        os.chmod(registro, 0o644)
    registro.write_text(f"{sha}  fonte-{aaaamm}.zip\n", encoding="utf-8")
    os.chmod(destino, 0o444)  # congelada
    # ⚠ O registro de custódia congela junto com o arquivo. Um sha256 gravável
    # ao lado de um zip 444 não protege nada: quem alterasse a fonte poderia
    # ajustar a impressão digital para combinar. Auditoria 16/09/2026 (B-7c).
    os.chmod(registro, 0o444)

    pacote = {
        "status": "ACEITO",
        "publicado": True,
        "competencia": comp,
        "gerado_em": datetime.now(UTC).isoformat(),
        "url": url,
        "zip_bytes": recebido,
        "zip_sha256": sha,
        "csv_membro": membros[0],
        "csv_bytes": csv_bytes,
        "gates": {
            "http_200": True,
            "bytes_conferem": True,
            "zip_valido": True,
            "membro_unico": True,
            "congelado_444": True,
        },
        "segundos": round(time.time() - t0),
    }
    (BASE / "evidence" / f"fetch-{aaaamm}.json").write_text(
        json.dumps(pacote, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nFETCH ACEITO · {comp}")
    print(f"  zip   : {recebido:,} bytes")
    print(f"  csv   : {csv_bytes:,} bytes descompactado")
    print(f"  sha256: {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
