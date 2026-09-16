---
name: novo-agente
description: |
  Gera um par de agentes (architect + developer) para uma ferramenta nova da
  fábrica, a partir de uma entrada de menu. O agente nasce conhecendo a doutrina
  do projeto, os defeitos catalogados e as pastas congeladas.

  Use quando: entrar uma tecnologia nova no pipeline (Polars, Dagster, Iceberg,
  Great Expectations...) e você quiser um agente que a conheça sem repetir todo
  o contexto da fábrica a cada conversa.
---

# novo-agente — gerador de agentes da fábrica

Uma ferramenta nova entra no pipeline. Em vez de explicar a doutrina toda vez,
você adiciona **uma entrada de menu** e o gerador produz dois agentes que já
sabem o que é proibido aqui.

## Por que gerar em vez de escrever à mão

Escrito à mão, cada agente novo repete (ou esquece) as mesmas regras: pastas
congeladas, tolerância zero, join pelo código. Um agente que esquece uma delas é
pior que nenhum — ele propõe a saída fácil com confiança.

Gerando, a doutrina entra por template. **Se ela mudar, `--refresh` propaga para
todos.**

---

## Uso

```bash
# 1. adicionar a tech ao menu
$EDITOR .claude/skills/novo-agente/menu/techs.yaml

# 2. gerar
bash .claude/skills/novo-agente/scaffold.sh polars

# 3. verificar (obrigatório — o gerador pode falhar em silêncio)
bash .claude/skills/novo-agente/quality-gate.sh --strict
```

Saída: `.claude/agents/polars-architect.md` e `.claude/agents/polars-developer.md`.

---

## A separação que o gate protege

| Papel | Tem `Bash`? | Por quê |
|---|---|---|
| **architect** | ❌ **não** | planeja. Sem execução, não há mudança acidental. |
| **developer** | ✅ sim | implementa e roda as evals. |

Isso não é convenção — é **verificado**. O `quality-gate.sh` emite `BLOCKER` se
um architect tiver Bash, e sai com código 7 em `--strict`.

> A razão é a mesma da nossa cerca: separar quem decide de quem executa. Um
> architect com Bash pode "só testar rapidinho" e alterar estado.

---

## Anatomia de uma entrada de menu

```yaml
polars:
  display_name: Polars
  description: "Polars — DataFrames em Rust, lazy evaluation, out-of-core"
  primary_language: python
  threshold_architect: 0.90      # confiança mínima para agir sem escalar
  threshold_developer: 0.95      # developer exige mais: ele muda estado
  color_architect: cyan
  color_developer: cyan
  capabilities_architect:
    - "Decidir o que fica em Polars vs DuckDB no Silver"
    - "Planejar processamento out-of-core para os 11,7 GB da fonte"
  capabilities_developer:
    - "Escrever LazyFrame que não materializa antes do necessário"
    - "Garantir Decimal em coluna monetária — nunca Float64"
  maxim: "Lazy até o último momento. Decimal sempre que for dinheiro."
  mission_architect: "Desenhar o caminho onde o dado grande não vira memória."
  mission_developer: "Entregar transformação que passa nos gates de soma."
```

**`threshold_developer` é maior de propósito.** Quem muda estado precisa de mais
certeza que quem só propõe.

---

## O que todo agente gerado herda

Sem você escrever:

```text
A doutrina           "Preserve o defeito. Recuse o lote. Verde pelo motivo certo."
Pastas congeladas    _raw/ · contracts/ · docs/adrs/
Os 4 defeitos        DF-INSS-001..004, com o tratamento de cada
Anti-patterns        tolerância em dinheiro, agrupar por nome, inventar descrição
As 3 evals           como rodar e o que cada uma prova
Handoff              architect → Bruno → developer → fabrica-reviewer
```

---

## Manutenção

```bash
# a doutrina mudou? propaga para todos os agentes
bash .claude/skills/novo-agente/scaffold.sh --refresh

# verificar tudo
bash .claude/skills/novo-agente/quality-gate.sh --strict
```

⚠️ **Arquivo gerado não se edita à mão.** Se precisar mudar o corpo de um agente,
mude o template ou a entrada de menu e regenere — senão o `--refresh` sobrescreve
sua edição sem avisar.

---

## Limites — o que este gerador não faz

- **Não preenche conhecimento específico da tech.** Ele gera o esqueleto com a
  doutrina; quem sabe Polars é você. As seções `capabilities` vêm do menu.
- **Não instala dependência.** Adicionar `polars` ao menu não roda `pip install`.
- **Não cria KB.** O repo-fonte gera árvore de KB, mas lá ela nasceu vazia (só
  TODO). Preferimos não gerar pasta que ninguém preenche.
