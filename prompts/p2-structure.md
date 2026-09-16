# P2 — Structure

**Onde:** Claude Code, **com o repositório aberto**.
**Emite arquivo?** **Não** — de propósito.
**Por que não emite:** este passe carrega contexto. Se emitisse arquivo e você
trocasse de sessão, perderia tudo que ele leu. Por isso P2 e P3 rodam **na mesma
sessão**.

---

## Cole isto

```
Ancorar a intenção do P1 no repositório real. NÃO escreva arquivo neste passe.

INTENÇÃO (saída do P1)
<cole aqui>

LEIA ANTES DE RESPONDER — nesta ordem
1. CLAUDE.md                doutrina e estado
2. contracts/layout.yaml    O JUIZ: colunas, defeitos, regras
3. docs/adrs/*.md           o que já foi decidido e não se re-litiga
4. AGENTS.md                que agentes existem
5. os arquivos que a mudança tocaria

SEU TRABALHO

1. ONDE ISSO ENCAIXA
   Que arquivos mudam? Que camada? Bronze, Silver, Gold, evals?

2. O QUE JÁ EXISTE E RESOLVE PARTE DISSO
   Não reimplemente. Cite o que já faz o trabalho.

3. CONFLITO COM DECISÃO TOMADA
   Algum ADR proíbe o caminho óbvio? Qual, e por quê?
   Se a intenção exige mudar um ADR aceito, PARE e diga —
   revisão se faz com ADR novo, nunca editando o antigo.

4. PASTAS CONGELADAS
   Toca _raw/, contracts/ ou docs/adrs/? Se sim, qual é o custo real?

5. QUE GATE PROVA
   Qual eval reprova se a mudança estiver errada? Já existe, ou precisa nascer?

6. RISCO DE FUSÃO SILENCIOSA
   A mudança pode agrupar categorias distintas sem que o total acuse?
   (É o padrão do DF-INSS-002: 34 de 65 espécies se fundem pelo nome, e a
   soma continua batendo.)

REGRAS
- Cite arquivo e linha em toda afirmação sobre o código.
- Não escreva arquivo. Não gere código. Não crie Task-Spec.
- Se algo estiver ambíguo no contrato, diga CONTRACT_AMBIGUITY e pare.

SAÍDA (no chat, sem arquivo)
## Encaixe
| Arquivo | Camada | O que muda |

## Já existe
<o que reaproveitar, com caminho>

## Conflitos
<ADR ou contrato que restringe — ou "nenhum">

## Congelado
<toca? qual custo?>

## Gate que prova
<comando; se não existir, o que precisa nascer>

## Risco de fusão silenciosa
<sim/não, e onde>
```

---

## A pergunta 6 é a mais importante

Uma mudança pode estar **certa em cada linha** e ainda fundir categorias. O
exemplo real deste projeto: agrupar espécie pelo nome truncado junta 34 de 65
códigos — e o total continua batendo, então nenhum gate de soma acusa.

Por isso o P2 pergunta isso explicitamente, antes de existir código.
