# ADR 0002 — Decimal, nunca float

- Status: Accepted. Vinculante.
- Data: 2026-09-15
- Decisor: Bruno (owner)
- Evidência: `contracts/layout.yaml` (`controle.sum_vl_liquido`) · os 3 packets

## Contexto

`Vl Líquido` chega como texto pt-BR com padding: `"        1.621,00"` — ponto de
milhar, vírgula decimal, largura 16.

O total de controle da fonte é **78.521.752.562,12** sobre 41.572.553 linhas.
Ponto flutuante binário não representa centavos exatamente; somar 41 milhões de
valores em `float64` acumula erro de arredondamento na casa dos centavos.

O contrato exige `sum(silver) == sum(bronze)` com **tolerância zero**. Com float,
essa igualdade falharia ou passaria por acaso — e passar por acaso é pior.

## Decisão

Todo valor monetário é `DECIMAL(18,2)`. Nunca `float`, `double` ou `REAL`.

O parse é `replace('.','') → replace(',','.') → cast(decimal(18,2))`.
Comparações são exatas. **Não existe banda de tolerância.**

## O que isto não é

Não é decisão sobre modo de arredondamento (não há arredondamento no Silver — os
valores vêm com 2 casas da fonte), nem sobre o tipo no Parquet do Bronze, onde
tudo é string por definição de camada.

## Consequências

- Bronze guarda o texto cru; a conversão acontece no Silver.
- `vl_medio` no Gold usa `round(avg(...), 2)` — é derivado, não um valor de fonte.
- Um `float` em caminho de dinheiro é gate reprovado.
- A igualdade das somas nas três camadas é verificável, não aproximada.
