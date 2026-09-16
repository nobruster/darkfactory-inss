# Fábrica INSS — referência rápida

Cole isto na cabeça antes de mexer em qualquer coisa.

## A doutrina

> Sem juiz, não se constrói. Preserve o defeito. Recuse o lote.
> Verde pelo motivo certo.

A fonte tem defeitos reais. A fábrica **classifica**, nunca corrige. Corrigir em
silêncio destrói a prova de que a origem tem um problema — e sem prova, ninguém
cobra quem mandou o dado errado.

## Congelado — escrita proibida

```
_raw/         bytes originais · chmod 444 · sha256
contracts/    O JUIZ
docs/adrs/    decisões vinculantes
```

Revisão de ADR se faz com **ADR novo que supersede**, nunca editando o antigo.

## Os 4 defeitos

| ID | O quê | Tratamento | Classificação |
|---|---|---|---|
| `DF-INSS-001` | coluna `Espécie` duplicada (pos 12 e 13) | leitura **posicional** | `CONFIRMED_SOURCE_DEFECT` |
| `DF-INSS-002` | truncamento em 20 chars funde 34 de 65 códigos | join pelo **código** | `CONFIRMED_SOURCE_DEFECT` |
| `DF-INSS-003` | código na fonte, fora do dicionário oficial | complemento separado | `CONTRACT_AMBIGUITY` |
| `DF-INSS-004` | fonte × dicionário divergem em 29 códigos | ambas preservadas | `CONTRACT_AMBIGUITY` |

## Números que não mudam sem ADR

```
41.572.553 linhas          2026-01
78.521.752.562,12          soma de controle 2026-01
27                         UFs (cobertura nacional)
65                         espécies no dicionário oficial
44                         nomes distintos após truncar em 20  ← o dano
66                         rótulos com o complemento
998                        banco que NÃO é banco (INSS direto)
```

## Provar antes de dizer que funcionou

```bash
make qa                      # lint + testes + gate dos agentes (sem dados)
make evals COMP=AAAA-MM      # as 3 evals de integração
```

A `eval_doutrina` compara **rótulos × nomes truncados**. Se alguém reintroduzir
agrupamento por nome, o número cai de 66 para 53 e ela reprova — sem precisar
saber *como* o erro foi cometido.

## Sempre BLOCKER

| Achado | Fonte |
|---|---|
| `float` em caminho monetário | ADR 0002 |
| tolerância em comparação de dinheiro | ADR 0002 |
| agrupar espécie/banco por nome | ADR 0003 · DF-INSS-002 |
| ler coluna por nome | ADR 0001 · DF-INSS-001 |
| inventar descrição para órfão | DF-INSS-003 |
| banco 998 como instituição financeira | ADR 0005 |
| deduplicar linhas | base anonimizada (LGPD) |
| remover ou afrouxar gate | a doutrina |

## Conceitos

- [por que o truncamento é grave](concepts/fusao-silenciosa.md)
- [classificar × corrigir](concepts/classificar-nao-corrigir.md)
- [publicação atômica](patterns/publicacao-atomica.md)
