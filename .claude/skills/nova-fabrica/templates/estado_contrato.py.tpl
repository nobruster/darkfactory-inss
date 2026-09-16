#!/usr/bin/env python3
"""O contrato está medido? Sem isso, a fábrica não constrói.

Este é o PRIMEIRO gate que esta fábrica executa — e ele é contra ela mesma.

Uma fábrica gerada nasce com o contrato cheio de `null` e `medido: false`.
Se o Bronze rodasse assim, ele compararia os totais contra nada, publicaria
ACEITO, e a primeira coisa que a fábrica produziria seria uma mentira com
aparência de evidência.

Por que não deixar o gerador medir sozinho e já nascer pronto: porque um
número que ninguém viu ser medido é indistinguível de um palpite. O custo de
`make perfil` (~1 min) compra a diferença entre juiz e decoração.

Uso:
  python3 scripts/estado_contrato.py                 # relatório
  python3 scripts/estado_contrato.py --breve         # uma linha, para o help
  python3 scripts/estado_contrato.py --exigir-medido # sai 1 se não medido
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]
CONTRATO = BASE / "contracts" / "layout.yaml"


def pendencias(c: dict) -> list[str]:
    """O que ainda falta medir. Lista vazia = contrato completo."""
    faltando = []

    if not c.get("colunas"):
        faltando.append("colunas: [] — `make perfil` lê o cabeçalho real")

    f = c.get("fonte") or {}
    for campo in ("colunas", "zip_sha256", "terminador"):
        if f.get(campo) is None:
            faltando.append(f"fonte.{campo}: null — medido por `make perfil`")

    if not c.get("controle_por_particao"):
        faltando.append(
            "controle_por_particao: {} — a ÂNCORA. `make ancora` mede, "
            "`make contrato` registra"
        )

    return faltando


def main() -> int:
    ap = argparse.ArgumentParser(description="estado de medição do contrato")
    ap.add_argument("--exigir-medido", action="store_true",
                    help="sai com 1 se o contrato não estiver medido")
    ap.add_argument("--breve", action="store_true",
                    help="uma linha só, para o make help")
    args = ap.parse_args()

    if not CONTRATO.exists():
        print(f"sem {CONTRATO.relative_to(BASE)} — esta fábrica não tem juiz")
        return 1

    c = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    medido = bool(c.get("medido"))
    falta = pendencias(c)

    if args.breve:
        if medido and not falta:
            n = len(c.get("controle_por_particao") or {})
            print(f"  contrato: MEDIDO · {n} partição(ões) ancorada(s)")
        else:
            print(f"  contrato: NAO_MEDIDO · {len(falta)} pendência(s) — make perfil")
        return 0

    if medido and not falta:
        ancoras = c.get("controle_por_particao") or {}
        print(f"CONTRATO MEDIDO · {len(c.get('colunas') or [])} colunas · "
              f"{len(ancoras)} partição(ões) ancorada(s)")
        for p, a in sorted(ancoras.items()):
            print(f"  {p}  {a.get('count_linhas'):>12,} linhas  "
                  f"medido em {a.get('medido_em')}")
        return 0

    # ── não medido ───────────────────────────────────────────────────
    print("CONTRATO NAO_MEDIDO — a fábrica recusa construir")
    print()
    if falta:
        print("  pendências:")
        for p in falta:
            print(f"    - {p}")
    if not medido:
        print("    - medido: false — vire true só depois de `make contrato`")
    print()
    print("  O caminho:")
    print("    make fetch      baixa e congela a fonte")
    print("    make perfil     varre e mede layout, domínios, cobertura")
    print("    make ancora     mede count e soma direto da fonte")
    print("    make contrato   transfere o medido para o contrato")
    print()
    print("  Isto não é burocracia. Um contrato com null no lugar do total")
    print("  faz o gate comparar contra nada e publicar ACEITO — que é")
    print("  exatamente o defeito que a auditoria do INSS encontrou.")

    if args.exigir_medido:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
