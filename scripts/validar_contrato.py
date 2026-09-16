#!/usr/bin/env python3
"""Testa o contrato contra os dados reais.

O contrato erra ou a fonte erra? Este script diz qual — comparando os
domínios declarados em `contracts/layout.yaml` com o que aparece nas
41 milhões de linhas.

Não corrige nada. Quando um domínio diverge, o achado é o resultado.

Uso:
  python3 scripts/validar_contrato.py --competencia 2026-03
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import sys
import zipfile
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="valida o contrato contra os dados")
    ap.add_argument("--competencia", help="AAAA-MM; padrão: a do contrato")
    args = ap.parse_args()

    contrato = yaml.safe_load(
        (BASE / "contracts" / "layout.yaml").read_text(encoding="utf-8")
    )
    especies = json.loads(
        (BASE / "contracts" / "_especies.json").read_text(encoding="utf-8")
    )

    comp = args.competencia or contrato["competencia"]
    aaaamm = comp.replace("-", "")
    fonte = BASE / "_raw" / f"fonte-{aaaamm}.zip"
    if not fonte.exists():
        print(f"sem fonte para {comp}. rode antes:")
        print(f"  python3 ingestion/fetch_fonte.py --competencia {comp}")
        return 1

    # domínios que o contrato declara como lista fechada
    declarados = {
        col["nome"]: set(col["dominio"])
        for col in contrato["colunas"]
        if isinstance(col.get("dominio"), list)
    }
    posicao = {col["nome"]: col["pos"] for col in contrato["colunas"]}
    ncols = contrato["fonte"]["colunas"]

    observado: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    especies_vistas: collections.Counter = collections.Counter()
    contagem_colunas: collections.Counter = collections.Counter()
    total = 0

    z = zipfile.ZipFile(fonte)
    membro = z.namelist()[0]
    with z.open(membro) as f:
        texto = io.TextIOWrapper(f, encoding=contrato["fonte"]["encoding"])
        texto.readline()  # descarta o cabeçalho ambíguo — lemos por posição
        for linha in texto:
            partes = linha.rstrip("\r\n").split(";")
            contagem_colunas[len(partes)] += 1
            if len(partes) < ncols:
                continue
            total += 1
            for campo in declarados:
                observado[campo][partes[posicao[campo]].strip()] += 1
            especies_vistas[partes[12].strip().zfill(2)] += 1

    print(f"competência: {comp}")
    print(f"linhas: {total:,}")
    print(f"contagem de colunas: {dict(contagem_colunas)}")
    print()

    violacoes = 0
    for campo, dominio in declarados.items():
        vistos = set(observado[campo])
        extras = vistos - dominio
        ausentes = dominio - vistos
        status = "VIOLADO" if extras else "OK"
        if extras:
            violacoes += 1
        print(f"[{status:8}] {campo}")
        if extras:
            print(f"           nos dados mas NÃO no contrato: {sorted(extras)}")
        if ausentes:
            print(f"           no contrato mas não nos dados: {sorted(ausentes)}")

    # DF-INSS-003 — código na fonte, ausente do dicionário oficial.
    # É CONTRACT_AMBIGUITY: registra e escala, não é violação do contrato.
    orfas = set(especies_vistas) - set(especies)
    print()
    status = "AMBIGUO" if orfas else "OK"
    print(f"[{status:8}] especie_codigo × dicionário oficial")
    print(f"           códigos nos dados: {len(especies_vistas)} | "
          f"no dicionário: {len(especies)}")
    if orfas:
        print(f"           ÓRFÃOS (sem descrição oficial): {sorted(orfas)}")
        print("           → CONTRACT_AMBIGUITY · ver DF-INSS-003")

    print()
    print(f"RESULTADO: {violacoes} violação(ões) de domínio"
          + (f" · {len(orfas)} espécie(s) órfã(s)" if orfas else ""))
    return 1 if violacoes else 0


if __name__ == "__main__":
    sys.exit(main())
