# Dark Factory INSS — contexto do projeto

Fábrica de dados que responde: **quanto cada instituição financeira movimenta
em benefícios do INSS, por unidade federativa?**

Remote: https://github.com/nobruster/darkfactory-inss

---

## ⚠️ A regra que governa tudo

> **Sem juiz, não se constrói. Preserve o defeito. Recuse o lote.
> Verde pelo motivo certo.**

A fonte tem defeitos reais e catalogados. A fábrica **classifica**, nunca
corrige. Corrigir em silêncio destrói a prova de que a origem tem um problema —
e sem prova, ninguém consegue cobrar quem mandou o dado errado.

**Quando um gate reprova, o trabalho é investigar — nunca ajustar a
expectativa para fazer passar.** Essa é a única coisa proibida sem exceção.

---

## Estado em 16/09/2026

| Competência | Linhas | Valor | Agregados |
|---|---|---|---|
| 2026-01 | 41.572.553 | R$ 78.521.752.562,12 | 418 |
| 2026-02 | 41.522.152 | R$ 78.441.374.955,39 | 437 |
| 2026-03 | 41.719.140 | R$ 78.771.556.568,72 | 465 |

**Pendentes:** 2025-12, 2025-11, 2025-10
**Resultado:** TOP 4 bancos concentram ~75,8% — estrutural, varia em centésimos.

---

## Como rodar

```bash
make init                 # venv + dependências (só na primeira vez)
make all COMP=2026-03     # fetch → bronze → silver → gold
make status               # o que rodou, em que competência
make ranking COMP=2026-03 # top bancos
```

**Cada etapa é um script Python.** O Makefile só encadeia — nada de `curl`,
`sed` ou lógica dentro dele: o que decide fica versionado e testável.

O download **nunca rebaixa** o que já existe (`make check` pergunta ao servidor
sem baixar; `make refetch` força, só com intenção explícita).

---

## Pastas congeladas — escrita proibida

```
_raw/         os bytes originais (chmod 444 + sha256)
contracts/    O JUIZ
docs/adrs/    decisões vinculantes
```

Protegido por `.claude/settings.json` e `.cvg/gate.yaml`.
**Revisão de ADR se faz com ADR novo, nunca editando o antigo.**

---

## Os 4 defeitos catalogados

| ID | Defeito | Tratamento |
|---|---|---|
| `DF-INSS-001` | coluna `Espécie` duplicada (pos 12 e 13) | leitura **posicional**; leitura por nome perde o código em silêncio |
| `DF-INSS-002` | truncamento em 20 chars funde 34 de 65 códigos | join pelo **código**, nunca pelo nome |
| `DF-INSS-003` | código 67 na fonte, fora do dicionário oficial | complemento separado; XLSX oficial **intocado** |
| `DF-INSS-004` | fonte × dicionário divergem em 29 códigos | ambas preservadas (`especie_nome` e `especie_nome_fonte`) |

### Por que o DF-INSS-002 importa

`'Aposentadoria Invali'` esconde **seis** espécies distintas — de incapacidade
permanente (3,3M benefícios) a aeronauta (26). Agrupar por nome somaria seis
políticas públicas numa linha, **e o total continuaria correto**: nada acusaria
o erro.

O mesmo com bancos: `756` (Sicoob) e `748` (Sicredi) viram `Banco Cooperativ`.

### A decisão sobre o 67 (16/09/2026)

Recusamos editar `especies-oficial.xlsx`. Seria trivial — 6 linhas em 41,7
milhões — mas o arquivo deixaria de ser o publicado pelo INSS e o checksum
quebraria. Em vez disso: `contracts/especies-complemento.yaml`, com
`especie_nome_origem` marcando a procedência.

```
dicionario_oficial   65 códigos · 41.719.134 linhas
fonte                 1 código  ·          6 linhas
```

**A ambiguidade continua aberta** e escalada ao INSS. O complemento documenta,
não resolve.

---

## Os 5 ADRs

| # | Decisão |
|---|---|
| [0001](docs/adrs/0001-leitura-posicional.md) | leitura posicional, nunca por nome |
| [0002](docs/adrs/0002-decimal-nunca-float.md) | decimal, nunca float |
| [0003](docs/adrs/0003-especie-join-pelo-codigo.md) | espécie pelo código |
| [0004](docs/adrs/0004-duas-nomenclaturas-preservadas.md) | as duas nomenclaturas preservadas |
| [0005](docs/adrs/0005-inss-direto-fora-do-ranking.md) | o INSS não é banco (sentinela 998) |

---

## Task-Spec e evals

`tasks/T-20260915-processar-competencia.md` — assinada (HMAC v3) e **ACEITA em
Tier 1**. 3 evals executáveis:

```bash
.venv/bin/python scripts/eval_packets.py   --competencia AAAA-MM   # B-1
.venv/bin/python scripts/eval_coerencia.py --competencia AAAA-MM   # B-2, B-3
.venv/bin/python scripts/eval_doutrina.py  --competencia AAAA-MM   # B-4..B-7
```

A `eval_doutrina` compara **rótulos × nomes truncados**: se alguém reintroduzir
o agrupamento por nome, o número cai e a eval reprova — sem precisar saber
*como* o erro foi cometido.

---

## O Hermes gerencia (degrau 1)

Bot Telegram `@factory_inss_bot`, job `fabrica-inss-vigia` às 9h e 21h.

- **Vigia e avisa. NUNCA processa sem autorização explícita do Bruno.**
- SOUL: `C:\Users\nobru\AppData\Local\hermes\SOUL.md`
- Ponte Windows→WSL: `C:\Users\nobru\Documents\dark_factory_2\fabrica.cmd`
- Contrato completo: [docs/OPERADOR.md](docs/OPERADOR.md)

⚠️ Ao mudar o SOUL: reiniciar o gateway **e apagar a sessão**
(`hermes sessions delete <id> --yes`) — senão ele mantém o contexto antigo.

---

## Armadilhas deste ambiente

1. **Repositórios clonados pelo Windows quebram no WSL** (CRLF). Aconteceu com
   `converge`, `task-spec` e as fixtures do Northwind. Clone sempre pelo WSL.
2. **Bind-mount de arquivo único falha em `/mnt/c/`** — por isso o projeto
   mora no disco Linux nativo.
3. **`pyarrow` precisa ser 25.x** — versões diferentes codificam os mesmos
   dados em bytes diferentes, e o golden-match compara bytes.
4. **Use `.venv/bin/python`**, nunca o `python3` do sistema.

---

## O que NÃO fazer

- editar `_raw/`, `contracts/` ou `docs/adrs/` para fazer um gate passar
- agrupar espécie ou banco pelo **nome** (funde categorias em silêncio)
- inventar descrição para código órfão — é `CONTRACT_AMBIGUITY`, escala
- tratar o banco `998` como instituição financeira (é o INSS pagando direto)
- **deduplicar linhas** — a base é anonimizada (LGPD), duplicatas são legítimas
- rebaixar a fonte quando ela já existe
