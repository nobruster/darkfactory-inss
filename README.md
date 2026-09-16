# Dark Factory — INSS Benefícios Emitidos

Fábrica de dados que responde: **quanto cada instituição financeira movimenta em
benefícios do INSS, por unidade federativa?**

Construída sobre 41,5 milhões de registros de pagamento (jan/2026), com contrato,
gates e evidência em cada etapa.

---

## A resposta

```
TOP 4 concentram 75,82% dos R$ 78,5 bilhões pagos em jan/2026

 1  237  Bradesco          R$ 18.763.085.923,02   23,90%
 2  104  Caixa Econômica   R$ 14.111.488.422,78   17,97%
 3  341  Itaú              R$ 13.358.115.254,76   17,01%
 4  001  Banco do Brasil   R$ 13.302.858.058,35   16,94%
```

---

## A regra que governa tudo

> **Sem juiz, não se constrói. Preserve o defeito. Recuse o lote.
> Verde pelo motivo certo.**

A fonte tem defeitos reais. A fábrica **não os corrige** — ela os classifica,
preserva a evidência e recusa publicar quando um gate reprova.

Corrigir em silêncio destrói a prova de que a origem tem um problema.

---

## Como rodar

```bash
make init                      # venv + dependências
make all                       # fetch -> bronze -> silver -> gold
make status                    # o que rodou, em que competência
make ranking                   # top 10 bancos
```

Outra competência troca `COMP` — mas antes precisa de **âncora**:

```bash
make fetch  COMP=2026-02       # baixa e congela a fonte
make ancora COMP=2026-02       # ~50s medindo count e soma direto do ZIP
                               # registre o resultado em
                               # controle_por_competencia: (exige ADR)
make all    COMP=2026-02
make ranking COMP=2026-02 --uf "São Paulo"
```

**Sem âncora, a competência publica como `ACEITO_SEM_ANCORA`** — os dados
saem, mas nenhum gate de total rodou, e o `make status` marca `~?` em vez de
`OK`. Não é bloqueio, é honestidade: até 16/09/2026 a fábrica publicava esse
mesmo estado chamando-o de `ACEITO`, e 82 milhões de linhas foram para o Gold
sem nunca terem sido conferidas contra a fonte. Ver
[ADR 0006](docs/adrs/0006-auditoria-por-tres-modelos.md).

A âncora é medida **antes e independente** do Bronze. Bronze conferir contra
si mesmo não é gate.

**Cada etapa é um script Python** — o Makefile só encadeia. O download nunca
rebaixa o que já está no disco:

| Comando | Comportamento |
|---|---|
| `make fetch` | baixa **só se não existir**; senão confere o sha256 e sai |
| `make check` | pergunta ao servidor se a fonte mudou, **sem baixar** |
| `make refetch` | rebaixa deliberadamente (reprocessamento) |

Requisitos: Python 3.12+, ~2 GB de disco por competência, ~4 min de execução.

## Competências processadas

| | jan/2026 | fev/2026 |
|---|---|---|
| Linhas | 41.572.553 | 41.522.152 |
| Valor | R$ 78.521.752.562,12 | R$ 78.441.374.955,39 |
| TOP 4 | 75,82% | 75,84% |
| Órfãos de espécie | nenhum | **código 67** |

A concentração é **estrutural** — varia em décimos entre os meses.

⚠️ Fevereiro trouxe o código de espécie **67** (`Pecúlio Obrigatório`), ausente do
dicionário oficial. A fábrica classificou como `CONTRACT_AMBIGUITY`, marcou as 3
linhas com `especie_orfa` e **não inventou** a descrição. Ver `DF-INSS-003`.

---

## Arquitetura

```
_raw/fonte.zip            575 MB · chmod 444 · sha256      ← congelado
   │
contracts/                O JUIZ · layout.yaml + 2 dicionários oficiais
   │                      Se o código e o contrato discordam, o contrato decide.
   ▼
landing/2026-01/          303 MB Parquet + sha256 + manifesto
   │                      leitura POSICIONAL · texto cru · 15 colunas
   ▼
lakehouse/2026-01/        DuckDB
   ├── silver             decimal(18,2) · data ISO · espécie resolvida
   └── gold               concentração bancária · grão (comp, banco, UF)
   │
evidence/                 um packet por execução, com os gates
```

### Os 15 gates

| Camada | Gates |
|---|---|
| **Bronze** | rejeições = 0 · count = 41.572.553 · soma = 78.521.752.562,12 |
| **Silver** | count/soma conferem com Bronze · espécie sem nulo · 65 rótulos · data sem nulo |
| **Gold** | soma confere (silver + contrato) · qtd confere · 27 UFs · grão único · INSS-direto separado e fora do ranking |

Se um gate reprova, **nada é publicado** — nem parcialmente.

---

## Os defeitos da fonte

Catalogados em `contracts/layout.yaml`, preservados, nunca corrigidos:

| ID | Defeito | Impacto |
|---|---|---|
| `DF-INSS-001` | coluna `Espécie` duplicada no cabeçalho | leitura por nome perde o código, em silêncio |
| `DF-INSS-002` | truncamento em 20 caracteres | 65 nomes viram 44 — 34 códigos perdem identidade |
| `DF-INSS-004` | fonte × dicionário oficial | 29 dos 65 códigos com nomenclatura divergente |

### Por que isso importa

`'Aposentadoria Invali'` esconde **seis** espécies distintas:

| Código | Espécie | Benefícios |
|---|---|---|
| 32 | Aposentadoria por incapacidade permanente | 3.316.548 |
| 92 | Invalidez Acidente Trabalho | 209.894 |
| 05 | Invalidez Acidentária - Trabalhador Rural | 1.951 |
| 06 | Invalidez Empregador Rural | 391 |
| 33 | Invalidez Aeronauta | 26 |
| 51 | Invalidez Extinto Plano Básico | 25 |

Agrupar por nome somaria seis políticas públicas numa linha — **e o total
continuaria correto**, então nada acusaria o erro.

A fábrica resolve pelo **código**, contra o dicionário oficial do INSS.

O mesmo vale para bancos: `756` (Sicoob) e `748` (Sicredi) aparecem ambos como
`Banco Cooperativ`. Fundidos, subiriam ao 5º lugar do ranking indevidamente.

---

## Decisões registradas

| ADR | Decisão |
|---|---|
| [0001](docs/adrs/0001-leitura-posicional.md) | leitura posicional, nunca por nome |
| [0002](docs/adrs/0002-decimal-nunca-float.md) | decimal, nunca float |
| [0003](docs/adrs/0003-especie-join-pelo-codigo.md) | espécie pelo código, nunca pelo nome |
| [0004](docs/adrs/0004-duas-nomenclaturas-preservadas.md) | as duas nomenclaturas preservadas |
| [0005](docs/adrs/0005-inss-direto-fora-do-ranking.md) | o INSS não é banco (sentinela 998) |

---

## O que é congelado

Escrita proibida — protegido por `.claude/settings.json` e `chmod 444`:

```
_raw/         os bytes originais — a fonte nunca se edita
contracts/    o juiz — a expectativa nunca se ajusta para passar
```

⚠️ Reescrever o juiz para virar vermelho em verde é trapaça, não conserto.
Quando o resultado diverge, o trabalho é **classificar**, não ajustar.

---

## A fonte

INSS · Plano de Dados Abertos 2025–2027 · Benefícios Emitidos

```
D.SDA.PDA.003.EMI.202601.CSV.ZIP    575.423.625 bytes
sha256  428626857daf30a3674d10b11bdd3f1ebd4a31d773de7c7ce5e3457f096f82e8
```

| | |
|---|---|
| Descompactado | 11,7 GB · encoding latin-1 · separador `;` |
| Registros | 41.572.553 |
| Cobertura | 27 UFs · 21 bancos · 65 espécies |
| Sem chave primária | anonimizado (LGPD) — duplicatas legítimas, **nunca deduplicar** |
