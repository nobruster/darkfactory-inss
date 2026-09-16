# {{DISPLAY_NAME}}

> {{PERGUNTA}}

Uma Dark Factory: pipeline medalhão onde **nenhuma camada publica sem passar
por um juiz**, e o juiz é um contrato versionado, não um teste que alguém
pode ajustar.

Gerada por [`nova-fabrica`](https://github.com/nobruster/darkfactory-inss) em {{DATA}}.

---

## Estado: o contrato ainda não foi medido

Esta fábrica **recusa construir**. Por design:

```console
$ make bronze
CONTRATO NAO_MEDIDO — a fábrica recusa construir

  pendências:
    - colunas: [] — `make perfil` lê o cabeçalho real
    - controle_por_particao: {} — a ÂNCORA
```

O contrato nasce vazio porque um número que ninguém viu ser medido é
indistinguível de um palpite — e um palpite no lugar do total faz o gate
comparar contra nada e publicar `ACEITO`.

---

## Começar

```bash
make init       # venv + dependências
make fetch      # baixa a fonte, congela em 444, grava o sha256
make perfil     # varre e mede: layout, domínios, cobertura
make ancora     # mede count e soma direto da fonte congelada
make contrato   # transfere o medido para o contrato (pede confirmação)
make all        # fetch → bronze → silver → gold
make evals      # prova o resultado
```

Requisitos: Python 3.12+.

---

## A doutrina

> **Sem juiz, não se constrói. Preserve o defeito. Recuse o lote.
> Verde pelo motivo certo.**

A fonte tem defeitos. A fábrica **não os corrige** — ela os classifica,
preserva a evidência e escala o que não sabe resolver.

| Código | Quando |
|---|---|
| `CONFIRMED_SOURCE_DEFECT` | a fonte mentiu, e dá para provar |
| `MODERN_DEFECT` | a fábrica errou — é nosso |
| `CONTRACT_AMBIGUITY` | discordam sem que um esteja errado |
| `UNRESOLVED` | não se sabe ainda |

---

## O que os gates garantem

| Gate | Tolerância |
|---|---|
| `count` e `soma` conferem com a âncora medida na fonte | **ZERO** |
| cada camada confere com a anterior **e** com a fonte | **ZERO** |
| coluna monetária é `DECIMAL`, nunca float | **ZERO** |
| chave declarada suspeita continua bijetiva | **ZERO** |
| linha fora do layout | **ZERO** — reprova o lote |
| pastas congeladas: 444 + sha256 | **ZERO** |

Gate reprovado = **ZERO artefato**. Publicação é atômica: `.parcial` +
`rename` só depois que todos os gates passam.

**Sem âncora, publica `ACEITO_SEM_ANCORA`** — visível no `make status` com
marca `~?`, nunca confundido com `ACEITO`.

---

## Pastas congeladas

`_raw/` · `contracts/` · `docs/adrs/` · `evidence/`

Protegidas por `.cvg/gate.yaml` **e** `.claude/settings.json` — duas cercas
que `make cercas` obriga a concordar. Duas cercas que discordam são uma
cerca com buraco.

**Revisão de ADR se faz com ADR novo, nunca editando o antigo.**

---

## Licença dos dados

Dados abertos. Verifique os termos da fonte antes de redistribuir.
