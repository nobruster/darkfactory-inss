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

| Agente | Classe | Faz | Arquivo |
|---|---|---|---|
| `fabrica-architect` | Architect | planeja mudança na fábrica, defende o contrato | [.claude/agents/fabrica-architect.md](.claude/agents/fabrica-architect.md) |
| `fabrica-reviewer` | Closer | revisa contra a doutrina, **roda as 3 evals** | [.claude/agents/fabrica-reviewer.md](.claude/agents/fabrica-reviewer.md) |
| `python-architect` | Architect | desenha script, streaming, packet de evidência | [.claude/agents/python-architect.md](.claude/agents/python-architect.md) |
| `python-developer` | Developer | Decimal, publicação atômica, argparse | [.claude/agents/python-developer.md](.claude/agents/python-developer.md) |
| `duckdb-architect` | Architect | grão do Gold, o que materializa | [.claude/agents/duckdb-architect.md](.claude/agents/duckdb-architect.md) |
| `duckdb-developer` | Developer | SQL com DECIMAL, soma exata entre camadas | [.claude/agents/duckdb-developer.md](.claude/agents/duckdb-developer.md) |
| `code-reviewer` | Closer | revisão genérica de código, BLOCKER/IMPORTANT/NIT | [.claude/agents/code-reviewer.md](.claude/agents/code-reviewer.md) |
| `code-simplifier` | Closer | remove código morto — **sabe o que não tocar** | [.claude/agents/code-simplifier.md](.claude/agents/code-simplifier.md) |
| `code-documenter` | Closer | docstrings, README, ADR no estilo do projeto | [.claude/agents/code-documenter.md](.claude/agents/code-documenter.md) |
| `codebase-explorer` | Explorer | mapeia repositório desconhecido | [.claude/agents/codebase-explorer.md](.claude/agents/codebase-explorer.md) |

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
