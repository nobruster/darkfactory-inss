# ADRs — Fábrica INSS Benefícios Emitidos

Registros de decisão de arquitetura. Cada um responde **o que é verdade e por quê**
— nunca instrução de como codar.

Todos são **vinculantes**: violar um é gate reprovado, não observação de estilo.

| # | Decisão | Defeito que endereça |
|---|---|---|
| [0001](0001-leitura-posicional.md) | Leitura posicional, nunca por nome | DF-INSS-001 · coluna `Espécie` duplicada |
| [0002](0002-decimal-nunca-float.md) | Decimal, nunca float | soma de 41,5M valores com tolerância zero |
| [0003](0003-especie-join-pelo-codigo.md) | Espécie pelo código, nunca pelo nome | DF-INSS-002 · truncamento funde 34 códigos |
| [0004](0004-duas-nomenclaturas-preservadas.md) | As duas nomenclaturas preservadas | DF-INSS-004 · fonte × dicionário, 29 divergências |
| [0005](0005-inss-direto-fora-do-ranking.md) | O INSS não é banco | sentinela `998` distorceria o ranking |

## O que um ADR aqui não faz

Não escolhe biblioteca, não prescreve implementação, não substitui o contrato.
O juiz é `contracts/layout.yaml`; estes documentos explicam **por que** ele diz
o que diz.

## Como verificar que ainda valem

Cada ADR aponta a evidência que o sustenta. Os números citados foram **medidos**,
não estimados:

```bash
cat evidence/bronze-run.json   # 41.572.553 linhas · soma confere
cat evidence/silver-run.json   # 29 divergências de nomenclatura
cat evidence/gold-run.json     # 7 gates · INSS-direto fora do ranking
```

Se um número mudar numa competência nova, o gate correspondente reprova — e aí
é investigar, não ajustar o ADR para caber.
