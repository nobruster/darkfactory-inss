# P1 — Intent

**Onde:** chat comum, **sem o repositório aberto**.
**Emite arquivo?** Não.
**Por que sem o repo:** o código existente enviesa. Aqui você decide o que
*quer*, não o que é fácil dado o que já está escrito.

---

## Cole isto

```
Você vai me ajudar a capturar a intenção de uma mudança antes de qualquer código.

CONTEXTO
Opero uma fábrica de dados sob contrato e gates. A doutrina é:
"Sem juiz, não se constrói. Preserve o defeito. Recuse o lote. Verde pelo
motivo certo." A fonte tem defeitos catalogados; a fábrica classifica,
nunca corrige.

O QUE QUERO
<descreva em 2-5 linhas, em linguagem de problema, não de solução>

SEU TRABALHO — me entreviste até estas perguntas terem resposta:

1. Qual problema real isso resolve? Quem sente a dor hoje?
2. Como saberemos que deu certo? Dê um critério FALSIFICÁVEL —
   algo que possa ser provado FALSO por um comando.
3. O que está explicitamente FORA de escopo?
4. Que defeito ou ambiguidade isso pode revelar?
5. Isso toca contrato, ADR ou pasta congelada? Se sim, por quê?
6. Qual o custo de NÃO fazer?

REGRAS
- Não proponha solução técnica ainda. Não escreva código.
- Se minha resposta for vaga, pergunte de novo. Não preencha lacuna por mim.
- Critério de sucesso que não pode ser reprovado não é critério — recuse.

SAÍDA (só depois da entrevista)
## Intenção
<uma frase>

## Problema
<o que dói hoje, com número se houver>

## Critério de sucesso (falsificável)
<o que, se acontecer, prova que falhou>

## Fora de escopo
<lista>

## Risco de defeito novo
<o que pode aparecer, e que classificação teria>

## Custo de não fazer
<consequência concreta>
```

---

## Por que "falsificável" importa tanto

| Não falsificável | Falsificável |
|---|---|
| "o pipeline deve ser confiável" | `sum(silver) == sum(bronze)`, tolerância zero |
| "tratar erros adequadamente" | linha com ≠14 colunas → rejeição, zero Parquet |
| "melhorar a performance" | 41M linhas em < 3 min, memória constante |

A coluna da esquerda sempre "passa" — ninguém consegue prová-la falsa. A da
direita **um agente verifica sozinho**, e é isso que torna a fábrica possível.
