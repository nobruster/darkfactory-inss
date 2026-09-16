#!/usr/bin/env python3
"""Transfere o que foi MEDIDO para o contrato — o único caminho sancionado.

O contrato nasce NAO_MEDIDO e a fábrica recusa construir. Este script é a
ponte, e ele existe para que essa ponte tenha regras:

  1. só promove o que tem arquivo de evidência. Número sem evidência é
     palpite, e palpite no contrato vira juiz de mentira.
  2. mostra o que vai mudar e PEDE CONFIRMAÇÃO. Uma medição que ninguém
     leu antes de virar âncora é uma medição que ninguém viu acontecer.
  3. destrava o contrato (444 -> 644), escreve, recongela.
  4. avisa que a mudança exige ADR: contracts/ é pasta congelada, e o CI
     bloqueia PR que mexa nela sem um ADR que a nomeie.

⚠ NÃO edite `medido: true` à mão. O gate de estado passaria a aprovar um
  contrato cujos números ninguém conferiu — que é exatamente o defeito
  que este desenho inteiro existe para impedir.

Uso:
  python3 scripts/promover_medicao.py --particao 2026-01
  python3 scripts/promover_medicao.py --particao 2026-01 --sim   # sem perguntar
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]
CONTRATO = BASE / "contracts" / "layout.yaml"


def carregar(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="promove medição para o contrato")
    ap.add_argument("--particao", required=True)
    ap.add_argument("--sim", action="store_true", help="não pergunta")
    args = ap.parse_args()

    part = args.particao
    chave = part.replace("-", "")

    texto = CONTRATO.read_text(encoding="utf-8")
    c = yaml.safe_load(texto)

    totais = carregar(BASE / "evidence" / f"_totais-{chave}.json")
    perfil = carregar(BASE / "evidence" / f"_perfil-{chave}.json")

    if totais is None:
        print(f"sem evidence/_totais-{chave}.json — a âncora não foi medida.")
        print(f"  rode antes:  make ancora PART={part}")
        return 1

    # ── o que vai mudar ──────────────────────────────────────────────
    print(f"── promover medição de {part} ──")
    print()
    print("  ÂNCORA (de evidence/_totais-%s.json):" % chave)
    for k, v in totais.items():
        if k in ("segundos", "particao", "competencia"):
            continue
        print(f"    {k:20} {v}")

    ancoras = c.get("controle_por_particao") or {}
    if part in ancoras:
        print()
        print(f"  ⚠ {part} JÁ tem âncora no contrato:")
        for k, v in ancoras[part].items():
            print(f"    {k:20} {v}")
        print()
        print("  Reescrever uma âncora existente é dizer que a medição")
        print("  anterior estava errada. Isso é ADR, não comando.")
        divergiu = [
            k for k in ("count_linhas", "sum_vl_liquido")
            if k in ancoras[part] and k in totais
            and str(ancoras[part][k]) != str(totais[k])
        ]
        if divergiu:
            print(f"  DIVERGE em: {divergiu}")
            print("  A fonte mudou ou a medição anterior estava errada.")
            print("  Investigue antes — não sobrescreva para 'destravar'.")
            return 1
        print("  (os números conferem — nada a fazer)")
        return 0

    if perfil is None:
        print()
        print(f"  ⚠ sem evidence/_perfil-{chave}.json")
        print("    O layout (colunas, terminador, sha256) não foi medido.")
        print(f"    Rode `make perfil PART={part}` para completar o contrato.")
        print("    Vou promover só a âncora; o contrato segue NAO_MEDIDO.")

    if not args.sim:
        print()
        resposta = input("  confirma? [s/N] ").strip().lower()
        if resposta not in ("s", "sim"):
            print("  cancelado — nada foi escrito")
            return 1

    # ── escrever ─────────────────────────────────────────────────────
    ancoras[part] = {
        k: v for k, v in totais.items()
        if k not in ("segundos", "particao", "competencia")
    }
    ancoras[part]["evidencia"] = f"evidence/_totais-{chave}.json"
    c["controle_por_particao"] = ancoras

    if perfil:
        fonte = c.setdefault("fonte", {})
        for campo in ("colunas", "terminador", "zip_sha256", "zip_bytes",
                      "arquivo_bytes"):
            if campo in perfil:
                fonte[campo] = perfil[campo]
        if perfil.get("colunas_detalhe"):
            c["colunas"] = perfil["colunas_detalhe"]

    # `medido` só vira true quando NADA mais está pendente. Meia-medição
    # não destrava a fábrica: seria pior que nenhuma, porque pareceria
    # completa.
    completo = bool(c.get("colunas")) and bool(c.get("controle_por_particao")) \
        and (c.get("fonte") or {}).get("colunas") is not None
    c["medido"] = completo
    c["estado"] = "MEDIDO" if completo else "NAO_MEDIDO"

    if CONTRATO.exists():
        os.chmod(CONTRATO, 0o644)
    CONTRATO.write_text(
        yaml.safe_dump(c, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    os.chmod(CONTRATO, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    print()
    print(f"  contrato atualizado · estado: {c['estado']}")
    if completo:
        print("  a fábrica já constrói:  make all PART=%s" % part)
    else:
        print("  ainda NAO_MEDIDO — veja o que falta:")
        print("    python3 scripts/estado_contrato.py")
    print()
    print("  ⚠ contracts/ é pasta congelada. Esta mudança precisa de ADR")
    print("    que NOMEIE layout.yaml, senão o CI bloqueia o PR.")
    print("    Atualize também contracts/CHECKSUMS.txt:")
    print("      python3 scripts/refrescar_checksums.py --confirmo-que-existe-adr")
    return 0


if __name__ == "__main__":
    sys.exit(main())
