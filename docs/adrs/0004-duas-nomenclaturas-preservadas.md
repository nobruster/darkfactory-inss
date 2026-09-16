# ADR 0004 — As duas nomenclaturas são preservadas

- Status: Accepted. Vinculante.
- Data: 2026-09-15
- Decisor: Bruno (owner)
- Classificação: `CONTRACT_AMBIGUITY` — escalado, não resolvido
- Evidência: DF-INSS-004 no contrato · `evidence/silver-run.json`

## Contexto

A fonte (SUIBE) e o dicionário oficial do INSS **discordam em 29 dos 65 códigos**
(medido). Há três naturezas de divergência:

| Tipo | Exemplo |
|---|---|
| Abreviação | `Aposent. Invalidez A` × `Aposentadoria Invalidez Acidentária...` |
| Acentuação | `Auxílio Doenca` × `Auxílio Doença` |
| **Nomenclatura legal** | cód. 31: `Auxílio Doenca Previ` × `Auxílio por Incapacidade Temporária` |

O terceiro caso não é erro de digitação. A **EC 103/2019** (Reforma da
Previdência) renomeou espécies: "Auxílio-Doença" virou "Auxílio por Incapacidade
Temporária"; "Aposentadoria por Invalidez" virou "Aposentadoria por Incapacidade
Permanente".

**O sistema operacional do INSS mantém a nomenclatura anterior; o dicionário
oficial publica a atual.** Ambos são fontes oficiais, e ambos estão corretos
dentro do seu próprio contexto.

## Decisão

A fábrica **não escolhe**. O Silver preserva as duas:

| Campo | Origem |
|---|---|
| `especie_nome` | dicionário oficial — nomenclatura pós-EC 103/2019 |
| `especie_nome_fonte` | como o SUIBE gravou — nomenclatura operacional |
| `especie_nome_confere` | `false` nos 29 códigos divergentes |

O Gold usa `especie_rotulo` (código + nome oficial). Quem precisa do nome
operacional tem `especie_nome_fonte` disponível.

## O que isto não é

Não é declaração de que o dicionário está certo e a fonte errada — nem o
contrário. Não é correção de dado. Não é decisão final: está **escalado ao dono
do dado** para definir qual nomenclatura é canônica em relatório externo.

## Consequências

- `count(distinct especie_codigo where not especie_nome_confere) == 29` é um gate.
  Se virar 30, apareceu divergência nova: investigar, não ajustar o número.
- Descartar `especie_nome_fonte` apagaria a evidência da ambiguidade — proibido.
- Relatório que cite nome de espécie deve declarar **qual** nomenclatura usa.
- Este ADR não bloqueia o Gold: a ambiguidade é sobre rótulo, não sobre valor.
