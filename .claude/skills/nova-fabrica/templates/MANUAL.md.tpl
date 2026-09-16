# Manual — como iniciar esta fábrica

**{{DISPLAY_NAME}}**
Gerado por `nova-fabrica` em {{DATA}}.

> A pergunta que esta fábrica responde:
> **{{PERGUNTA}}**

---

## Antes de começar: o que você tem em mãos

Uma fábrica **gerada**, não pronta. A diferença importa:

| Está pronto | Falta você fazer |
|---|---|
| estrutura de pastas e Makefile | medir a fonte |
| gates, cercas, CI, ADRs semente | adaptar 8 scripts à sua fonte |
| doutrina inteira embutida | escrever a regra de negócio do Gold |

**A fábrica recusa construir agora.** Isso é proposital, não é defeito.

```console
$ make bronze
CONTRATO NAO_MEDIDO — a fábrica recusa construir
```

Se ela construísse, compararia os totais contra `null` e publicaria `ACEITO`.
Um `ACEITO` que não conferiu nada é pior que um erro: erro você vê.

---

## O caminho completo — 7 passos

Tempo total: **2 a 6 horas**, quase tudo no passo 5 (adaptar scripts).
Os passos 1–4 são mecânicos, ~15 minutos mais o download.

```
1. ambiente        make init
2. fonte           make fetch
3. layout          make perfil          ← aqui você CONFERE o que foi medido
4. âncora          make ancora
5. adaptar         (o trabalho de verdade)
6. promover        make contrato        ← a fábrica destrava aqui
7. construir       make all && make evals
```

---

## Passo 1 — ambiente

```bash
cd {{DESTINO_EXEMPLO}}
make init
```

Cria `.venv/` e instala duckdb, pyarrow, pyyaml, ruff, pytest, requests.
Exige Python 3.12+.

**Confira:** `make help` deve listar os alvos e mostrar
`contrato: NAO_MEDIDO · N pendência(s)`.

---

## Passo 2 — baixar e congelar a fonte

```bash
make fetch PART={{PARTICAO_EXEMPLO}}
```

O que acontece:

1. baixa de `{{URL_PADRAO}}`
2. grava em `_raw/fonte-<particao>.zip`
3. **`chmod 444`** — a fonte vira somente-leitura
4. grava o `.sha256` ao lado, **também 444**

> **Por que congelar.** A fonte é a única coisa que a fábrica não pode
> reproduzir. Se ela mudar, toda evidência já publicada deixa de provar o que
> dizia. O sha256 é a cadeia de custódia; ele congela junto com o arquivo
> porque uma impressão digital gravável ao lado de um arquivo travado não
> protege coisa nenhuma.

**Se a fonte já existe**, `make fetch` **não rebaixa** — confere o sha256 e sai.
Para rebaixar de propósito: `make refetch`.

**Confira:** `ls -la _raw/` — dois arquivos, ambos `-r--r--r--`.

---

## Passo 3 — medir o layout

```bash
make perfil PART={{PARTICAO_EXEMPLO}}
```

Varre a fonte e mede: número de colunas, encoding real, terminador de linha,
domínios de cada campo, cobertura. Escreve `evidence/_perfil-<particao>.json`.

### ⚠ Este é o passo onde você precisa olhar, não só rodar

O contrato **declara** encoding, separador e cabeçalho — valores que vieram do
menu e são **palpite até aqui**. O perfil confere contra os bytes reais.

**Encoding errado não estoura: corrompe acento em silêncio.** Se o perfil
disser que o encoding declarado não bate, pare e investigue. Não ajuste o
contrato para calar o aviso.

Leia a saída procurando:

- **colunas:** bate com o que você esperava?
- **valores estranhos** num campo: `{ñ class}`, `00000`, `NAO INFORMADO` —
  são **sentinelas**, não lixo. Registre no contrato. Nunca exclua nem impute.
- **campos truncados:** nome cortado em 20 ou 30 chars funde categorias
  distintas, e o total continua batendo. Foi o `DF-INSS-002`.

---

## Passo 4 — medir a âncora

```bash
make ancora PART={{PARTICAO_EXEMPLO}}
```

Varre a fonte inteira e mede `count`, `soma`, `mínimo`, `máximo` das colunas
monetárias. Escreve `evidence/_totais-<particao>.json`.

> **Por que isto é separado do Bronze.** A âncora é medida **antes e
> independente** da ingestão. Bronze conferir contra números que o próprio
> Bronze produziu não é gate — é o réu assinando o próprio alvará.
>
> Este é o ponto mais importante do manual inteiro. Ver
> [ADR 0003](adrs/0003-ancora-por-particao.md).

Leva cerca de 1 minuto por 40 milhões de linhas.

---

## Passo 5 — adaptar os scripts semente

**O trabalho de verdade.** Oito arquivos vieram do `darkfactory-inss` com
este aviso no topo:

```
# ⚠ SEMENTE A ADAPTAR — gerada por nova-fabrica
```

Eles **não rodam como estão**: a lógica ainda fala do INSS. O que você
preserva e o que troca:

| PRESERVE (é a doutrina) | TROQUE (é da fonte) |
|---|---|
| publicação atômica `.parcial` + `rename` | nomes de coluna |
| ZERO artefato quando gate reprova | parsing de data e número |
| gate de âncora, que nunca se desliga | regra de negócio do Gold |
| packet de evidência em toda execução | sentinelas e defeitos |

### A ordem que funciona

**5.1 `ingestion/fetch_fonte.py`** — provavelmente só a URL.

**5.2 `scripts/perfil_cobertura.py` e `totais_controle.py`** — índice da
coluna monetária e o parsing dela. (Se os passos 3 e 4 já rodaram, estes
dois já estão adaptados.)

**5.3 `ingestion/ingest_bronze.py`** — nomes das colunas. Bronze é **texto
cru**: não converte nada. Se você está fazendo `cast` aqui, é Silver.

**5.4 `scripts/build_silver.py`** — conformação: trim, `DECIMAL(18,2)` no
dinheiro, data em ISO-8601, separar código de nome.

**5.5 `scripts/build_gold.py`** — a regra de negócio. **É aqui que a
pergunta vira tabela.** Grão declarado: `{{GRAO_GOLD}}`.

**5.6 `scripts/eval_doutrina.py` e `tests/test_ancora.py`** — os testes.

### Três armadilhas que já custaram caro

**1. Agrupar por nome em vez de código.** Se dois códigos compartilham um
nome truncado, agrupar por nome funde duas categorias — **e o total continua
batendo**. Nada acusa. Agregue sempre pelo código.

**2. Chave composta que fragmenta.** O inverso da anterior, e mais traiçoeiro.
Um código que aparece sob muitos rótulos *parece* não-único. No INSS,
"5.563 de 5.572 códigos de município aparecem em mais de uma UF" sugeria a
chave `(uf, codigo)`. Medido: o código era **perfeitamente único** — a outra
UF era um segundo fato no mesmo registro. A "correção" teria partido São Paulo
em 27 municípios, e o total continuaria batendo.

> **Meça os dois sentidos antes de compor chave.** Fusão e fragmentação
> passam igual pelo gate de soma.

**3. `avg()` devolvendo float.** No DuckDB, `avg()` sobre `DECIMAL` retorna
`DOUBLE`. O defeito fica no **tipo**, não no valor: a soma bate e o centavo
se perde na borda. Sempre:

```sql
cast(round(avg(valor), 2) as decimal(18,2))
```

---

## Passo 6 — promover a medição

```bash
make contrato PART={{PARTICAO_EXEMPLO}}
```

Mostra o que vai mudar e **pede confirmação**. Só promove o que tem arquivo
de evidência.

`medido: true` só é escrito quando **nada** está pendente. Meia-medição não
destrava — seria pior que nenhuma, porque pareceria completa.

### Depois disto, `contracts/` está congelado

```bash
python3 scripts/refrescar_checksums.py --confirmo-que-existe-adr
```

E a mudança **exige um ADR que nomeie `layout.yaml`**, senão o CI bloqueia o
PR. Não é burocracia: é o que impede alguém de ajustar o juiz para um teste
passar.

**Confira:** `python3 scripts/estado_contrato.py` deve dizer `CONTRATO MEDIDO`.

---

## Passo 7 — construir e provar

```bash
make all PART={{PARTICAO_EXEMPLO}}
make evals PART={{PARTICAO_EXEMPLO}}
make status
```

### Leia o status com atenção

| Marca | Significa |
|---|---|
| `OK` | `ACEITO` — os gates rodaram e passaram |
| `~?` | `ACEITO_SEM_ANCORA` — **publicou sem juiz de total** |
| `!!` | `REJEITADO` — leia as falhas |

**`~?` não é sucesso.** Significa que aquela partição não tem âncora e nenhum
gate de total rodou. Volte ao passo 4.

### Antes de confiar: prove que o gate reprova

Um gate que nunca se viu reprovar é decoração.

```bash
# adultere a âncora em UM CENTAVO no contrato e rode make silver
# ele DEVE reprovar. Se passar, o gate não está ligado.
```

Depois desfaça. Este teste leva dois minutos e vale mais que ler o código.

---

## Partição nova, depois da primeira

```bash
make fetch   PART=<nova>
make ancora  PART=<nova>      # ~1 min — obrigatório
make contrato PART=<nova>     # exige ADR
make all     PART=<nova>
make evals   PART=<nova>
```

**Toda partição exige âncora própria.** Sem ela: `ACEITO_SEM_ANCORA`.

---

## Quando algo der errado

| Sintoma | Causa provável |
|---|---|
| `CONTRATO NAO_MEDIDO` | falta passo 3, 4 ou 6 — rode `estado_contrato.py` |
| `soma != âncora` | **NÃO ajuste o contrato.** A fonte mudou ou o parsing está errado |
| `rejeicoes > 0` | linha fora do layout. Investigue antes de relaxar a regra |
| `coluna monetária não-DECIMAL` | faltou `cast` depois de um `avg()` |
| `cercas divergem` | `settings.json` e `gate.yaml` discordam |
| `~?` no status | falta âncora para aquela partição |

### A regra que resolve a maioria

> Quando o resultado diverge do contrato, **classifique** — não conserte o
> contrato.

| Código | Quando |
|---|---|
| `CONFIRMED_SOURCE_DEFECT` | a fonte mentiu, e dá para provar |
| `MODERN_DEFECT` | a fábrica errou — é nosso, conserta-se |
| `CONTRACT_AMBIGUITY` | discordam sem que um esteja errado |
| `UNRESOLVED` | não se sabe ainda. É resposta legítima. |

⚠️ **O erro nº 1** é virar vermelho em verde mexendo na expectativa.
Reescrever o juiz é trapaça, não conserto.

---

## O que nunca fazer

- **Não** editar `medido: true` à mão. Use `make contrato`.
- **Não** editar packet em `evidence/`. Packet errado se **reexecuta**.
- **Não** editar ADR aceito. Mudou de ideia? **ADR novo que supersede.**
- **Não** ajustar o contrato para um teste passar.
- **Não** "corrigir" dado errado da fonte. Classifique.
- **Não** desligar gate para destravar. Se ele reprova, ele está funcionando.

---

## Checklist

```
[ ] 1. make init            .venv criado
[ ] 2. make fetch           _raw/ com zip + sha256, ambos 444
[ ] 3. make perfil          LI a saída; sentinelas anotadas
[ ] 4. make ancora          evidence/_totais-*.json existe
[ ] 5. adaptei os 8 scripts e apaguei os avisos ⚠ SEMENTE
[ ] 6. make contrato        estado_contrato.py diz MEDIDO
[ ]    refrescar_checksums + ADR que nomeia layout.yaml
[ ] 7. make all && make evals    tudo OK, nenhum ~?
[ ]    provei que o gate reprova (adulterei 1 centavo)
[ ] 8. make qa              lint, testes, cercas, agentes
[ ] 9. atualizei o CLAUDE.md com as partições processadas
```

---

## Para entender *por que*, não só *como*

- [`CLAUDE.md`](../CLAUDE.md) — a doutrina e o contexto
- [`adrs/0001`](adrs/0001-leitura-posicional.md) — ler por posição
- [`adrs/0002`](adrs/0002-decimal-nunca-float.md) — dinheiro é DECIMAL
- [`adrs/0003`](adrs/0003-ancora-por-particao.md) — **a âncora não se desliga**

O ADR 0003 conta como 82 milhões de linhas foram publicadas com `ACEITO` sem
que nada as tivesse conferido. Vale os cinco minutos.
