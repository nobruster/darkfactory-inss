# ADR 0001 — Leitura posicional, nunca por nome

- Status: Accepted. Vinculante.
- Data: 2026-09-15
- Decisor: Bruno (owner)
- Evidência: `contracts/layout.yaml` (`leitura.modo`) · `evidence/bronze-run.json`

## Contexto

O cabeçalho do CSV traz **`Espécie` duas vezes** — posições 12 e 13. A 12 é o
código de 2 dígitos; a 13 é o nome, truncado em 20 caracteres.

Testado com `csv.DictReader`: ele mantém a posição 13 e **descarta a 12 em
silêncio**. Sem erro, sem aviso. O mesmo vale para `pandas` (que renomeia para
`Espécie.1`) e para qualquer leitor que use o cabeçalho como chave.

A coluna que sobrevive à leitura ingênua é justamente a inutilizável: 65 códigos
distintos colapsam em 44 nomes truncados (medido).

## Decisão

Todo leitor desta fonte usa **índice posicional**, nunca o nome do cabeçalho.
O cabeçalho é descartado na primeira linha; os nomes vêm do contrato.

## O que isto não é

Não é escolha de biblioteca, nem regra para outros datasets do INSS, nem decisão
sobre qual das duas colunas é canônica — ambas são preservadas no Bronze.

## Consequências

- O Bronze grava 14 colunas com nomes do contrato: `especie_codigo` e
  `especie_nome_truncado`.
- Mudança na **ordem** das colunas da fonte quebra a ingestão ruidosamente — que
  é o comportamento desejado. Mudança de **nome**, não.
- Ler por nome neste projeto é gate reprovado, não observação de estilo.
