#!/usr/bin/env python3
"""As duas cercas de escrita têm de concordar.

A fábrica tem dois lugares que dizem "não escreva aqui":

  .cvg/gate.yaml           protected_paths — o teto do Converge
  .claude/settings.json    permissions.deny — o que o agente não faz

Até 16/09/2026 elas discordavam em silêncio: o gate protegia docs/adrs/ e o
settings não; o settings protegia validation/, que não existe. Duas cercas
que discordam são uma cerca com buraco, e ninguém sabe qual metade vale.

Este script não escolhe quem está certo. Ele acusa a divergência — se o
contrato é o juiz, a cerca também precisa de um.

Uso:
  python3 scripts/verificar_cercas.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]

# Caminhos que o gate protege mas que não fazem sentido como deny do agente:
# são padrões genéricos herdados do Converge (secrets, id_rsa) ou pastas que
# este projeto não tem. Isentá-los é decisão registrada, não esquecimento.
ISENTOS_NO_SETTINGS = {
    "**/.git/**", "**/.cvg/**", "**/.env", "**/.env.*",
    "**/secrets/**", "**/credentials/**", "**/*_key*", "**/*_secret*",
    "**/id_rsa*", "**/.terraform/**", "**/migrations/**",
    "**/auth/**", "**/payments/**", "**/billing/**",
}


def caminhos_do_settings() -> set[str]:
    """Extrai o alvo de cada regra deny: 'Write(contracts/**)' -> 'contracts/**'."""
    dados = json.loads(
        (BASE / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    alvos = set()
    for regra in dados.get("permissions", {}).get("deny", []):
        m = re.match(r"(Write|Edit)\((.+)\)$", regra)
        if m:
            alvos.add(m.group(2))
    return alvos


def main() -> int:
    gate = yaml.safe_load(
        (BASE / ".cvg" / "gate.yaml").read_text(encoding="utf-8")
    )
    protegidos = set(gate.get("protected_paths", []))
    exigidos = protegidos - ISENTOS_NO_SETTINGS
    no_settings = caminhos_do_settings()

    faltando = sorted(exigidos - no_settings)
    # Sobrando: o settings nega algo que o gate não protege. Não é furo de
    # segurança — é sinal de que uma das cercas ficou para trás.
    sobrando = sorted(no_settings - protegidos)

    if not faltando and not sobrando:
        print(f"OK · as duas cercas concordam em {len(exigidos)} caminhos")
        return 0

    print("CERCAS DIVERGEM:")
    for p in faltando:
        print(f"  gate.yaml protege {p!r}, settings.json não nega")
    for p in sobrando:
        print(f"  settings.json nega {p!r}, gate.yaml não protege")
    print("\n  Duas cercas que discordam são uma cerca com buraco.")
    print("  Alinhe as duas — ou registre a exceção em ISENTOS_NO_SETTINGS")
    print("  deste script, com o motivo.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
