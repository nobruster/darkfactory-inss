# Prompts — os 4 passes antes de escrever código

Metodologia de planejamento em quatro passes. São **prompts humanos**, para
copiar e colar — não código.

A ideia: a decisão errada custa mais que o código errado. Estes quatro passes
existem para que a decisão seja tomada com contexto, atacada por um adversário,
e só então virem tarefas.

## Por que quatro, e nesta ordem

```
P1 Intent          o que se quer, sem repositório aberto
P2 Structure       como isso encaixa no que já existe
P3 Decomposition   em que tarefas isso se divide
P4 Consensus       um MOTOR DIFERENTE tenta derrubar
```

**P4 é o que impede auto-aprovação.** Um modelo revisando o próprio plano
concorda consigo mesmo — ele repete os próprios pontos cegos. Por isso o passe
4 exige outro motor: outro Claude em janela nova, ou Codex, ou Gemini.

| Passe | Onde rodar | Emite arquivo? |
|---|---|---|
| P1 | chat, **sem** o repositório | não |
| P2 | Claude Code, repositório aberto | **não** |
| P3 | Claude Code, **mesma sessão do P2** | sim: Task-Specs |
| P4 | **outro motor** | sim: veredito |

P2 não emite arquivo de propósito — ele carrega contexto. Se emitisse, você
perderia esse contexto ao trocar de sessão. Por isso P2 e P3 ficam juntos.

## Quando usar

| Situação | Usa os 4 passes? |
|---|---|
| ferramenta nova no pipeline | ✅ sim |
| defeito novo na fonte | ✅ sim |
| mudança que toca contrato ou ADR | ✅ **sempre** |
| corrigir bug com causa conhecida | ❌ vai direto |
| processar competência nova | ❌ é rotina, tem Task-Spec |

## Os arquivos

- [`p1-intent.md`](p1-intent.md) — captura a intenção
- [`p2-structure.md`](p2-structure.md) — ancora no repositório real
- [`p3-decomposition.md`](p3-decomposition.md) — vira tarefas com eval
- [`p4-consensus.md`](p4-consensus.md) — o adversário ataca

## O que não fazer

- **Pular o P4 porque o plano parece bom.** Planos ruins parecem bons para quem
  os escreveu — é essa a razão do passe existir.
- **Rodar o P4 no mesmo motor.** Auto-revisão não é consenso.
- **Emitir código no P1 ou P2.** Nesses passes você está decidindo, não
  construindo.
