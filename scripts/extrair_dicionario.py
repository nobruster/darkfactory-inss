#!/usr/bin/env python3
"""Extrai `_especies.json` do XLSX oficial do INSS.

Este script existia só na minha cabeça: o `_especies.json` era consumido por
build_silver, validar_contrato e os testes, mas nenhum script no repositório o
gerava. A auditoria de 16/09/2026 apontou — o pipeline usava um dicionário sem
proveniência, sem checksum e editável.

Agora o JSON é derivado do XLSX congelado, e o CI confere o checksum de ambos.

Uso:
  python3 scripts/extrair_dicionario.py          # gera e compara
  python3 scripts/extrair_dicionario.py --check  # só compara, não escreve
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import openpyxl

BASE = Path(__file__).resolve().parents[1]
XLSX = BASE / "contracts" / "especies-oficial.xlsx"
JSON = BASE / "contracts" / "_especies.json"


def extrair() -> dict[str, str]:
    """Lê o XLSX oficial. Código vira string de 2 dígitos — `01`, nunca `1`."""
    ws = openpyxl.load_workbook(XLSX, read_only=True).active
    especies: dict[str, str] = {}
    for linha in ws.iter_rows(values_only=True):
        if linha and isinstance(linha[0], int) and linha[1]:
            especies[f"{linha[0]:02d}"] = str(linha[1]).strip()
    return especies


def main() -> int:
    ap = argparse.ArgumentParser(description="extrai o dicionário oficial do XLSX")
    ap.add_argument("--check", action="store_true",
                    help="compara sem escrever; sai 1 se divergir")
    args = ap.parse_args()

    if not XLSX.exists():
        print(f"sem {XLSX.relative_to(BASE)} — o dicionário oficial é congelado")
        return 1

    extraido = extrair()

    if JSON.exists():
        atual = json.loads(JSON.read_text(encoding="utf-8"))
        if atual == extraido:
            print(f"OK · {len(extraido)} espécies · JSON confere com o XLSX oficial")
            return 0
        so_json = set(atual) - set(extraido)
        so_xlsx = set(extraido) - set(atual)
        mudou = {k for k in set(atual) & set(extraido) if atual[k] != extraido[k]}
        print("DIVERGE do XLSX oficial:")
        if so_json:
            print(f"  só no JSON (foi adicionado à mão?): {sorted(so_json)}")
        if so_xlsx:
            print(f"  só no XLSX (JSON desatualizado): {sorted(so_xlsx)}")
        if mudou:
            print(f"  descrição diferente: {sorted(mudou)}")
        if args.check:
            print("\n  o JSON não deriva do XLSX. Regenere ou investigue —")
            print("  editar o dicionário à mão reescreve o juiz.")
            return 1

    if args.check:
        print(f"sem {JSON.relative_to(BASE)} — rode sem --check para gerar")
        return 1

    JSON.write_text(
        json.dumps(extraido, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"gerado · {len(extraido)} espécies · {JSON.relative_to(BASE)}")
    print("\n  atualize o checksum:")
    print("    cd contracts && sha256sum _especies.json >> CHECKSUMS.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
