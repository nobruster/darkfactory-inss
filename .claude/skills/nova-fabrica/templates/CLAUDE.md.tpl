# {{DISPLAY_NAME}} — Dark Factory

Claude lê este arquivo no início de toda sessão. É a memória do projeto.

Gerada por `nova-fabrica` em {{DATA}}, a partir do `darkfactory-inss`.

---

## A pergunta que esta fábrica responde

> {{PERGUNTA}}

Se uma tabela produzida aqui não ajuda a responder isso, ela é dump, não Gold.

---

## ⚡ ESTADO — leia antes de qualquer comando

**O contrato está `NAO_MEDIDO`.** A fábrica RECUSA construir. Isso não é bug
nem pendência: é o primeiro gate, e ele é contra a própria fábrica.

```bash
make init
make fetch      # baixa e congela a fonte (chmod 444 + sha256)
make perfil     # varre e mede layout, domínios, cobertura
make ancora     # mede count e soma direto da fonte congelada
make contrato   # transfere o medido para contracts/layout.yaml
make all        # só agora
```

Quando o contrato estiver medido, **atualize esta seção** com as partições
processadas e seus totais — como o INSS faz.

---

## A doutrina

> **Sem juiz, não se constrói. Preserve o defeito. Recuse o lote.
> Verde pelo motivo certo.**

A fonte tem defeitos reais. A fábrica **classifica**, nunca conserta:

| Código | Quando |
|---|---|
| `CONFIRMED_SOURCE_DEFECT` | a fonte mentiu, e dá para provar |
| `MODERN_DEFECT` | a fábrica errou — é nosso, conserta-se |
| `CONTRACT_AMBIGUITY` | fonte e contrato discordam sem que um esteja errado |
| `UNRESOLVED` | não se sabe ainda. É resposta legítima. |

⚠️ **Erro nº 1:** virar vermelho em verde mexendo na expectativa. Reescrever
o juiz é trapaça, não conserto.

---

## As regras que esta fábrica herdou (e por quê)

### A âncora nunca se desliga sozinha

O gate de total compara contra `controle_por_particao`, medido direto da
fonte **antes e independente** do Bronze. Sem âncora para a partição, publica
`ACEITO_SEM_ANCORA` — nunca `ACEITO` calado.

No INSS, esta linha aparentemente razoável:

```python
if comp == contrato["competencia"]:    # só aqui conferia
```

desligava o juiz em 2 de 3 competências, e o packet dizia `ACEITO` com
`"count_confere": false` escondido dentro. 82 milhões de linhas publicadas
sem conferência. Ver `docs/adrs/0003-ancora-por-particao.md`.

### Dinheiro é DECIMAL, nunca float

`avg()` no DuckDB devolve `DOUBLE`. O defeito fica no **tipo**, não no valor:
a soma continua batendo enquanto o centavo se perde na borda. Há gate que
acusa coluna `vl_*` não-DECIMAL no Gold.

### Chave só é chave se for bijetiva

Um código que deixa de ser único faz a agregação somar coisas diferentes —
**e o total continua batendo**. Cada coluna em `chaves_suspeitas` ganha gate.

⚠️ O inverso também engana: um código que aparece sob muitos rótulos pode ser
um segundo fato no mesmo campo. Chave composta errada **fragmenta** a
entidade, e o total bate do mesmo jeito. Meça os dois sentidos.

### Evidência não se edita

Packet errado se **reexecuta**. Conferência retroativa vira arquivo **novo**,
ao lado do antigo. Os dois ficam no git — esse é o ponto.

### Congelado é 444 + sha256 + CI

`_raw/` · `contracts/` · `docs/adrs/`. Permissão impede o acidente, checksum
prova que não houve acidente. Só uma das duas é metade.

O `.sha256` congela **junto** com o arquivo: registro de custódia gravável ao
lado de fonte 444 não protege nada.

---

## Estrutura

```
contracts/layout.yaml     O JUIZ. Congelado. NAO_MEDIDO até você medir.
ingestion/                fetch (congela) · bronze (fonte → Parquet)
scripts/                  perfil · âncora · silver · gold · evals
docs/adrs/                decisões vinculantes. Não se edita, supersede-se.
evidence/                 packets: a prova do que rodou, e quando
_raw/                     a fonte congelada
```

---

## Ao retomar uma sessão

1. `make status` — o que rodou, em que partição
2. `python3 scripts/estado_contrato.py` — o contrato já foi medido?
3. `ls evidence/` — vazio significa que nada rodou ainda
4. Não repita o que já foi feito. Não pule o que não foi.

---

## O que NÃO fazer

- Não editar `contracts/`, `docs/adrs/` ou `evidence/` sem ADR.
- Não marcar `medido: true` à mão. Use `make contrato`.
- Não "corrigir" dado errado — o método classifica, não repara.
- Não afirmar número sem ter medido. Se não deu para verificar, diga isso.
