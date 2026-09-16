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
make init      # cria o venv e instala dependências
make fetch     # baixa a fonte (575 MB) e congela: chmod 444 + sha256
make all       # bronze -> silver -> gold
make status    # estado dos packets de evidência
make ranking   # top 10 bancos
```

Requisitos: Python 3.12+, ~2 GB de disco, ~5 min de execução.

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
