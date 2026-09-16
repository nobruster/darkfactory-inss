# Agentes — Dark Factory INSS

Índice de roteamento no padrão [agents.md](https://agents.md/). Vale para Claude
Code, Codex, Cursor e qualquer harness que leia este arquivo.

**Fonte de verdade:** `.claude/agents/`. Este arquivo é índice, não conteúdo.

---

## Classes

| Classe | Tem `Bash`? | Quando usar |
|---|---|---|
| **Architect** | ❌ não | planejar antes de escrever código |
| **Developer** | ✅ sim | implementar e provar com as evals |
| **Closer** | varia | antes de commitar |
| **Explorer** | ✅ sim | entender código que você não escreveu |

A separação architect/developer é **verificada**, não convencionada:
`quality-gate.sh` emite `BLOCKER` se um architect tiver Bash.

---

## Agentes

### Da fábrica (transversais)

| Agente | Classe | Faz |
|---|---|---|
| `fabrica-architect` | Architect | planeja mudança, defende o contrato |
| `fabrica-reviewer` | Closer | revisa contra a doutrina, **roda as 3 evals** |

### Por superfície de decisão

| Agente | Classe | Faz |
|---|---|---|
| `contrato-architect` / `-developer` | ⚠️ threshold **0.98** | o juiz: defeitos, domínios, totais de controle |
| `evidencia-architect` / `-developer` | Architect / Developer | packets, cadeia de custódia sha256 |
| `operacao-architect` / `-developer` | Architect / Developer | Makefile, operador, rotina do Hermes |

### Por tecnologia

| Agente | Classe | Faz |
|---|---|---|
| `python-architect` / `-developer` | Architect / Developer | streaming, Decimal, publicação atômica |
| `duckdb-architect` / `-developer` | Architect / Developer | grão do Gold, SQL com DECIMAL |

### Universais

| Agente | Classe | Faz |
|---|---|---|
| `code-reviewer` | Closer | revisão genérica, BLOCKER/IMPORTANT/NIT |
| `code-simplifier` | Closer | remove código morto — **sabe o que não tocar** |
| `code-documenter` | Closer | docstrings, README, ADR |
| `codebase-explorer` | Explorer | mapeia repositório desconhecido |

**16 agentes.** Todos em [.claude/agents/](.claude/agents/), todos aprovados pelo
`quality-gate.sh`.

> **Sobre `contrato-*` ter threshold 0.98:** é o mais alto do projeto. Mexer no
> juiz é a decisão mais cara que existe aqui — abaixo dessa confiança, escala.

---

## Qual usar

```text
vou mudar algo no pipeline           → fabrica-architect  (planeja)
                                     → python/duckdb-developer  (implementa)
                                     → fabrica-reviewer   (revisa + evals)

achei código estranho                → codebase-explorer
antes de commitar                    → code-reviewer
sobrou código morto                  → code-simplifier
falta docstring / README             → code-documenter
```

**`fabrica-reviewer` × `code-reviewer`:** o primeiro conhece a doutrina, os 4
defeitos e roda as evals. O segundo é revisão genérica de qualidade. Para
mudança no pipeline, use o primeiro.

---

## Ferramenta nova

Entrou Polars, Dagster, Iceberg no pipeline? Gere o par:

```bash
$EDITOR .claude/skills/novo-agente/menu/techs.yaml   # descomente ou adicione
bash .claude/skills/novo-agente/scaffold.sh polars
bash .claude/skills/novo-agente/quality-gate.sh --strict
```

O agente nasce conhecendo a doutrina, os defeitos e as pastas congeladas.

⚠️ **Não gere agente para ferramenta que não está no pipeline.** Um conselheiro
de dbt num projeto sem dbt recomenda o que não existe aqui. (Foi por isso que o
`dbt` está comentado no menu.)

---

## Convenções

- **Arquivo gerado não se edita à mão** — mude o menu ou o template e regenere;
  `scaffold.sh --refresh` sobrescreve.
- **Agente novo passa pelo gate** antes de ser usado.
- **Doutrina e defeitos** vivem em [CLAUDE.md](CLAUDE.md) e [docs/adrs/](docs/adrs/) —
  os agentes referenciam, não duplicam.
- **Números de confiança** em [.claude/doctrine.yaml](.claude/doctrine.yaml);
  regras de operação em [.claude/rules/](.claude/rules/).
