#!/usr/bin/env python3
"""Operador — a interface da fábrica para um agente (Hermes ou outro).

Degrau 2 de autonomia: EXECUTA e REPORTA. Não decide.

O que este script faz:
  - descobre competências pendentes na fonte oficial
  - roda o pipeline de uma competência
  - devolve um relatório em JSON, pronto para virar mensagem

O que ele NÃO faz, por desenho:
  - não edita contrato, ADR ou qualquer pasta congelada
  - não classifica defeito — quem classifica é a fábrica
  - não decide sobre órfão ou ambiguidade: escala

Uso:
  python3 scripts/operador.py pendentes            # o que falta processar
  python3 scripts/operador.py processar 2026-03    # roda uma competência
  python3 scripts/operador.py relatorio 2026-03    # lê o que já rodou
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
URL = ("https://armazenamento-dadosabertos.s3.sa-east-1.amazonaws.com/"
       "PDA_2025_2027/Grupos_de_dados/Benef%C3%ADcios+emitidos/"
       "D.SDA.PDA.003.EMI.{aaaamm}.CSV.ZIP")


def existe_remoto(aaaamm: str) -> int | None:
    """Tamanho em bytes se a competência existe na fonte oficial; None se não."""
    try:
        req = urllib.request.Request(URL.format(aaaamm=aaaamm), method="HEAD",
                                     headers={"User-Agent": "darkfactory-inss/1.0"})
        with urllib.request.urlopen(req, timeout=45) as r:
            return int(r.headers.get("Content-Length", 0))
    except Exception:
        return None


def processada(comp: str) -> bool:
    aaaamm = comp.replace("-", "")
    return all((BASE / "evidence" / f"{c}-{aaaamm}.json").exists()
               for c in ("bronze", "silver", "gold"))


def competencias_candidatas(meses: int = 12) -> list[str]:
    """Os últimos N meses, do mais recente para trás.

    12 por padrão: o INSS publica com atraso (em 16/09/2026 a última
    disponível era 2026-03). Uma janela curta esconde competências reais.
    """
    hoje = date.today()
    out = []
    ano, mes = hoje.year, hoje.month
    for _ in range(meses):
        out.append(f"{ano:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
    return out


def cmd_pendentes(args) -> int:
    pendentes, ja_feitas = [], []
    for comp in competencias_candidatas(args.meses):
        if processada(comp):
            ja_feitas.append(comp)
            continue
        tamanho = existe_remoto(comp.replace("-", ""))
        if tamanho:
            pendentes.append({"competencia": comp, "bytes": tamanho})

    print(json.dumps({
        "acao": "pendentes",
        "pendentes": pendentes,
        "ja_processadas": ja_feitas,
        "mensagem": (
            f"{len(pendentes)} competência(s) disponível(is) e não processada(s): "
            + ", ".join(p["competencia"] for p in pendentes)
            if pendentes else "nada pendente — a fábrica está em dia"
        ),
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_processar(args) -> int:
    comp = args.competencia
    r = subprocess.run(["make", "all", f"COMP={comp}"], cwd=BASE,
                       capture_output=True, text=True)
    relatorio = montar_relatorio(comp)
    relatorio["acao"] = "processar"
    relatorio["exit_code"] = r.returncode
    if r.returncode != 0:
        relatorio["stderr"] = r.stderr[-1500:]
    print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    return 0 if relatorio["status"] == "ACEITO" else 1


def montar_relatorio(comp: str) -> dict:
    aaaamm = comp.replace("-", "")
    camadas, escalar = {}, []
    for c in ("bronze", "silver", "gold"):
        f = BASE / "evidence" / f"{c}-{aaaamm}.json"
        if not f.exists():
            camadas[c] = {"status": "NAO_EXECUTADO"}
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        camadas[c] = {"status": d.get("status"), "linhas": d.get("linhas"),
                      "falhas": d.get("falhas", [])}
        if c == "bronze":
            camadas[c]["soma"] = d.get("sum_vl_liquido")
        if c == "silver":
            orf = (d.get("DF-INSS-003") or {}).get("codigos_orfaos") or []
            if orf:
                camadas[c]["orfaos"] = orf
                escalar.append({
                    "tipo": "CONTRACT_AMBIGUITY",
                    "detalhe": f"espécie(s) {orf} na fonte e ausente(s) do "
                               f"dicionário oficial ({d['DF-INSS-003']['linhas_afetadas']} linhas)",
                    "acao_humana": "decidir se o dicionário será atualizado; "
                                   "a fábrica NÃO inventa descrição",
                })

    reprovadas = [c for c, v in camadas.items() if v["status"] not in ("ACEITO",)]
    status = "ACEITO" if not reprovadas else "REPROVADO"

    if status == "ACEITO":
        msg = (f"{comp} processada · {camadas['bronze'].get('linhas', 0):,} linhas · "
               f"R$ {camadas['bronze'].get('soma', '?')}")
        if escalar:
            msg += f" · {len(escalar)} item(ns) para você decidir"
    else:
        det = "; ".join(f"{c}: {camadas[c].get('falhas')}" for c in reprovadas)
        msg = f"{comp} REPROVADA em {', '.join(reprovadas)} — {det}"
        escalar.append({
            "tipo": "GATE_REPROVOU",
            "detalhe": det,
            "acao_humana": "investigar. NÃO ajustar contrato nem expectativa "
                           "para fazer passar",
        })

    return {"competencia": comp, "status": status, "camadas": camadas,
            "escalar_para_humano": escalar, "mensagem": msg}


def cmd_relatorio(args) -> int:
    print(json.dumps(montar_relatorio(args.competencia), indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="interface da fábrica para agentes")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pendentes", help="competências disponíveis e não processadas")
    p.add_argument("--meses", type=int, default=12)
    p.set_defaults(func=cmd_pendentes)

    p = sub.add_parser("processar", help="roda o pipeline de uma competência")
    p.add_argument("competencia")
    p.set_defaults(func=cmd_processar)

    p = sub.add_parser("relatorio", help="lê o que já rodou")
    p.add_argument("competencia")
    p.set_defaults(func=cmd_relatorio)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
