---
id: T-20260915-processar-competencia
title: "Processar uma competência do INSS da fonte ao Gold"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: claude
parent: docs/adrs/README.md
depends_on: []
supersedes: (none)

touches_paths: []
creates_paths:
  - landing/
  - lakehouse/
  - evidence/
source_note: "contracts/layout.yaml v2 · ADR 0001..0005"
created: 2026-09-16T02:19:44Z
tags: [inss, medallion, etl]
owner: bruno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "a fonte da competência existe em _raw/ e o sha256 confere"
blocked_reason: (none)
security_class: dados_abertos_anonimizados
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: true
signed_off_by: nobru
signed_off_at: 2026-09-16T02:29:16Z
accepted: false
accepted_by: (none)
accepted_at: (none)
evidence_refs: []
signed_off_sig: hmac-sha256-v3:c80659a9:e970d2d40da374110ac078d77f516e58be418335afdd29cd82a06c8eaccc5062
---

# "Processar uma competência do INSS da fonte ao Gold"

> **Why:** os dados de benefícios emitidos revelam concentração bancária real —
> quatro instituições movimentam 75% de R$ 78 bilhões mensais. A fonte tem
> defeitos que, tratados ingenuamente, fundem categorias em silêncio.

---

## Goal

Levar uma competência do arquivo bruto até o agregado de concentração bancária,
com todos os gates passando e um packet de evidência por camada. A fábrica
**classifica** defeitos da fonte; nunca os corrige.

---

## Context

O contrato (`contracts/layout.yaml`) é o juiz: declara 14 colunas lidas por
posição, os defeitos conhecidos, os sentinelas e as regras de aceitação.

Três defeitos catalogados que a execução deve **preservar**:

- `DF-INSS-001` — a coluna `Espécie` aparece duas vezes; leitura por nome
  descarta o código em silêncio
- `DF-INSS-002` — truncamento em 20 caracteres funde 34 de 65 espécies
- `DF-INSS-003` — código na fonte e ausente do dicionário oficial
  (`CONTRACT_AMBIGUITY`: classifica, não inventa descrição)

Os totais de controle do contrato valem **só** para a competência que ele
declara. Em outra, a coerência entre camadas continua obrigatória; os totais
absolutos, não.

---

## Behavior

- **B-1** — Toda linha tem 14 colunas; rejeição > 0 falha e nada é publicado.
- **B-2** — `sum(bronze) == sum(silver) == sum(gold)`, tolerância ZERO.
- **B-3** — `count(bronze) == count(silver) == sum(gold.qtd_beneficios)`.
- **B-4** — Espécie resolvida pelo **código** contra o dicionário oficial.
  Código órfão marca `especie_orfa` e **não** falha a execução.
- **B-5** — Banco `998` tem linha própria e `posicao_na_uf` nula.
- **B-6** — Gold cobre 27 UFs; grão `(competencia, banco_codigo, uf)` é único.
- **B-7** — Nada em `_raw/`, `contracts/` ou `docs/adrs/` é alterado.

---

## Success Criteria

As evals **executam** a fábrica e leem a evidência real. Nenhuma afirma que algo
existe.

```bash
# eval-1: a linha completa roda e os três packets saem ACEITO
eval_1() {
  make all COMP="${COMP:-2026-01}" || return 1
  .venv/bin/python scripts/eval_packets.py --competencia "${COMP:-2026-01}"
}

# eval-2: o valor atravessa as camadas sem perder um centavo
eval_2() {
  .venv/bin/python scripts/eval_coerencia.py --competencia "${COMP:-2026-01}"
}

# eval-3: a doutrina foi respeitada (espécie, 998, UFs, congelados)
eval_3() {
  .venv/bin/python scripts/eval_doutrina.py --competencia "${COMP:-2026-01}"
}
```

---

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: a linha completa roda e os tres packets saem ACEITO
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: true
    expected_duration_sec: 300
  - id: eval_2
    description: sum e count atravessam bronze/silver/gold sem divergir
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_3
    description: especie pelo codigo, 998 fora do ranking, 27 UFs, congelados intactos
    runnable: bash
    check_type: deterministic
    verifies: [B-4, B-5, B-6, B-7]
    terminal: true
    expected_duration_sec: 10

retry_policy:
  max_iterations: 15
  circuit_breaker_no_progress: 3
  on_terminal_failure: park_with_context

agent_contract:
  version: 2
  read: [intent, behavior, contract, guardrails, operations]
  produce:
    - code
    - config
  required_tools: [git, bash, make, python3]
  timeout_minutes: 30
  sandbox_type: host
  output_artifacts:
    - evidence/bronze-*.json
    - evidence/silver-*.json
    - evidence/gold-*.json
  mcp_dependencies: []
  emit:
    - pass
    - fail
    - retry_with_reason
    - parked_with_context
  backend_metadata: {}
```

---

## Exit Check

```bash
# Prova final. Retorna 0 só quando as três evals passam.
eval_1 && eval_2 && eval_3
```

---

## Rollback Plan

```bash
make clean CONFIRM=clean-runtime COMP="${COMP:-2026-01}"
```

Apaga `landing/`, `lakehouse/` e os packets **daquela competência**. Fonte e
contratos permanecem — são congelados, fora do runtime.

Nenhuma etapa publica parcialmente: cada camada grava em `.parcial` e só renomeia
depois dos gates. Um rollback nunca encontra estado intermediário.

---

## Observability Hooks

- `make status` — o que rodou, em que competência, com que resultado
- `evidence/<camada>-<AAAAMM>.json` — gates, contagens, somas
- `landing/<COMP>/parquet-manifest.json` — cadeia de custódia
  (`fonte_sha256` → `parquet_sha256`)

---

## Anti-Patterns

- **Ajustar o contrato para um teste passar.** Se diverge, classifica-se.
- **Agrupar espécie pelo nome.** Funde 34 de 65 códigos e o total continua
  batendo — o erro fica invisível.
- **Inventar descrição para código órfão.** É `CONTRACT_AMBIGUITY`: escala.
- **Tratar o banco 998 como instituição financeira.** Distorce o ranking.
- **Deduplicar linhas.** A base é anonimizada; duplicatas são legítimas.
- **Rebaixar a fonte por reflexo.** Só com `--force`.

---

## Do-Not-Touch

```
_raw/**          a fonte: bytes originais, chmod 444
contracts/**     o juiz
docs/adrs/**     decisões vinculantes — revisão é por ADR novo
```

Protegido por `.claude/settings.json` e `.cvg/gate.yaml`.

---

## Open Questions

1. O código municipal do SUIBE (5 dígitos) não tem de-para público para IBGE.
   Enriquecimento geográfico depende disso. Dono: Bruno.
2. `DF-INSS-004` — fonte e dicionário usam nomenclaturas de épocas diferentes em
   29 dos 65 códigos. Qual é canônica para relatório externo? Escalado ao dono
   do dado.
