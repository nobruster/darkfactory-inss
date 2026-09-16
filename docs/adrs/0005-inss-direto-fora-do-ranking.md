# ADR 0005 — O INSS não é banco

- Status: Accepted. Vinculante.
- Data: 2026-09-15
- Decisor: Bruno (owner)
- Evidência: `contracts/layout.yaml` (`sentinelas."998"`) · `evidence/gold-run.json`

## Contexto

O campo `Banco` traz o código `998-Instituto Nacion`. Ele ocupa a mesma posição
dos códigos FEBRABAN (001 BB, 104 Caixa, 237 Bradesco), mas **não é instituição
financeira** — é o INSS pagando diretamente.

Volume em jan/2026: **153.378 benefícios, R$ 765.565.685,09**.

Tratado como banco, entraria no ranking de concentração bancária em posição
intermediária e distorceria os percentuais — respondendo errado à pergunta
"quanto cada instituição financeira movimenta".

## Decisão

`998` recebe linha própria no Gold, com `e_inss_direto = true`, e é **excluído
do ranking**: `posicao_na_uf` fica nulo para ele.

O valor **permanece** no total da UF e no total geral — não é descartado, apenas
não compete no ranking de bancos.

## O que isto não é

Não é exclusão do dado, nem filtro aplicado no Silver, nem regra para outros
sentinelas (`{ñ class}`, `00000-Zerada`, `Nao Informado`), que têm tratamento
próprio como categoria.

## Consequências

- `sum(gold.vl_total) == sum(silver.vl_liquido)` continua válido: o 998 está
  dentro do total.
- Dois gates verificam isto:
  - `inss_direto_separado` — a linha existe
  - `inss_direto_fora_do_ranking` — `posicao_na_uf` é nulo para o 998
- O percentual `pct_da_uf` do 998 é calculado normalmente — ele mostra quanto do
  pagamento na UF não passa por banco, que é informação útil.
- Ranking publicado deve dizer que exclui pagamento direto do INSS.
