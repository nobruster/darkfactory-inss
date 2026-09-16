# ADR 0003 — Espécie se resolve pelo código, nunca pelo nome

- Status: Accepted. Vinculante.
- Data: 2026-09-15
- Decisor: Bruno (owner)
- Evidência: `contracts/especies-oficial.xlsx` · DF-INSS-002 no contrato

## Contexto

O nome da espécie chega truncado em 20 caracteres. Medido sobre os 65 nomes
oficiais: **restam 44 após o truncamento — 13 grupos de colisão, 34 códigos
afetados (52% das espécies)**.

O caso mais grave, `'Aposentadoria Invali'`, funde **seis** espécies:

| Código | Espécie | Benefícios |
|---|---|---|
| 32 | Aposentadoria por incapacidade permanente | 3.316.548 |
| 92 | Invalidez Acidente Trabalho | 209.894 |
| 05 | Invalidez Acidentária - Trabalhador Rural | 1.951 |
| 06 | Invalidez Empregador Rural | 391 |
| 33 | Invalidez Aeronauta | 26 |
| 51 | Invalidez Extinto Plano Básico | 25 |

Agrupar por nome somaria seis políticas públicas distintas numa linha — e o total
continuaria correto, então **nada acusaria o erro**.

## Decisão

`especie_nome` vem de `join especie_codigo → contracts/especies-oficial.xlsx`.
O campo `especie_nome_truncado` **nunca** é usado para agrupar nem exibir.

Para exibição e agrupamento existe `especie_rotulo` = `código · nome oficial`
(ex: `41 · Aposentadoria por Idade`). É único por construção e sobrevive a
truncamento posterior em BI ou relatório, porque o código vem primeiro.

## O que isto não é

Não é decisão sobre qual nomenclatura é canônica (isso é o ADR 0004), nem
descarte do campo truncado — ele é preservado no Bronze como prova do defeito.

## Consequências

- O join exige `lpad(codigo, 2, '0')`: o código chega como `'    41'` e ler como
  inteiro transformaria `01` em `1`, quebrando a correspondência.
- `especie_nome` nulo significa join quebrado — é `MODERN_DEFECT`, não warning.
- `count(distinct especie_rotulo) == 65 > count(distinct especie_nome_truncado) == 44`
  é um gate. Se alguém reintroduzir o agrupamento por nome, o número cai e reprova.
- `especie_colide` marca os 34 códigos afetados, permitindo auditar o impacto.
