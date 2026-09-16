#!/usr/bin/env python3
"""Recalcula CHECKSUMS.txt dos artefatos congelados de contracts/.

Congelar é chmod 444 + sha256 registrado. As duas coisas: permissão impede o
acidente, checksum prova que não houve acidente. Só uma das duas é metade.

Este script é a ÚNICA forma sancionada de mexer no CHECKSUMS.txt — e só deve
rodar depois de um ADR que justifique a mudança no arquivo congelado.
Rodá-lo para "fazer o CI passar" é reescrever o juiz.

Uso:
  python3 scripts/refrescar_checksums.py --confirmo-que-existe-adr
"""
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DIR = BASE / "contracts"

# A ordem é a do arquivo atual — estável, para o diff do git ficar legível.
ARQUIVOS = [
    "especies-oficial.xlsx",
    "glossario-campos.xlsx",
    "especies-complemento.yaml",
    "layout.yaml",
    "_especies.json",
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirmo-que-existe-adr", action="store_true",
                    help="afirma que um ADR justifica esta mudança")
    args = ap.parse_args()

    if not args.confirmo_que_existe_adr:
        print("recuso: mexer no checksum de arquivo congelado exige ADR.")
        print("  Se a mudança é deliberada, escreva o ADR e rode com")
        print("  --confirmo-que-existe-adr")
        return 2

    faltando = [n for n in ARQUIVOS if not (DIR / n).exists()]
    if faltando:
        print(f"arquivos ausentes: {faltando}")
        return 1

    destino = DIR / "CHECKSUMS.txt"
    if destino.exists():
        os.chmod(destino, 0o644)
    linhas = [f"{sha256(DIR / n)}  {n}\n" for n in ARQUIVOS]
    destino.write_text("".join(linhas), encoding="utf-8")

    # recongela tudo: 444 é o estado normal destes arquivos
    for n in [*ARQUIVOS, "CHECKSUMS.txt", "_glossario.json"]:
        p = DIR / n
        if p.exists():
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    print(f"CHECKSUMS.txt regravado · {len(linhas)} artefatos · tudo em 444")
    for linha in linhas:
        sha, nome = linha.split()
        print(f"  {sha[:16]}…  {nome}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
