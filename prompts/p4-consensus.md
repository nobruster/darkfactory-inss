# P4 — Consensus

**Onde:** ⚠️ **MOTOR DIFERENTE** do que fez P1–P3. Outro Claude em janela nova,
Codex, Gemini — qualquer um, menos a mesma sessão.
**Emite arquivo?** Sim — o veredito.

---

## Por que outro motor

Um modelo revisando o próprio plano **concorda consigo mesmo**. Ele repete os
mesmos pontos cegos que teve ao planejar — não por má-fé, mas porque o
raciocínio que o levou ao plano é o mesmo que ele usa para avaliá-lo.

É a mesma razão pela qual o `golden_match` desta fábrica faz **duas perguntas
independentes** em vez de uma. Duas fontes que concordam não provam que estão
certas; podem estar erradas do mesmo jeito.

> Auto-revisão não é consenso.

---

## Cole isto no outro motor

```
Você é o ADVERSÁRIO. Seu trabalho é derrubar este plano, não aprová-lo.

CONTEXTO DO PROJETO
Fábrica de dados sob contrato e gates de tolerância zero. Doutrina:
"Sem juiz, não se constrói. Preserve o defeito. Recuse o lote. Verde pelo
motivo certo." A fonte tem defeitos catalogados; a fábrica classifica,
nunca corrige.

Pastas congeladas: _raw/ (bytes originais), contracts/ (o juiz),
docs/adrs/ (decisões vinculantes).

Defeitos conhecidos:
  DF-INSS-001  coluna Espécie duplicada → leitura posicional
  DF-INSS-002  truncamento em 20 chars funde 34 de 65 códigos
  DF-INSS-003  código na fonte fora do dicionário → complemento separado
  DF-INSS-004  fonte × dicionário divergem em 29 códigos

O PLANO
<cole P1, P2 e as Task-Specs do P3>

ATAQUE NESTES ÂNGULOS

1. FUSÃO SILENCIOSA
   Onde isto pode juntar categorias distintas sem que o total acuse?
   (É o padrão do DF-INSS-002.)

2. GATE FRACO
   Alguma eval passa sem provar o que diz provar?
   Alguma reprova por motivo diferente do declarado?

3. DEFEITO ESCONDIDO
   Isto corrige em silêncio algo que deveria classificar?

4. TOLERÂNCIA INFILTRADA
   Aparece float, arredondamento, "aproximadamente" em caminho de dinheiro?

5. RAIO MAIOR QUE O DECLARADO
   O que a tarefa realmente toca, além de creates_paths?

6. DEPENDÊNCIA NÃO DITA
   O plano assume estado que pode não existir? (lakehouse construído,
   competência processada, dicionário presente?)

7. O QUE ACONTECE QUANDO FALHA
   Se a metade der errado, sobra estado parcial? Publica lixo?

8. CUSTO OCULTO
   Tempo, memória, disco. 41,7M linhas e 11,7 GB de fonte.

REGRAS DO ATAQUE
- Toda objeção cita arquivo, ADR ou linha de contrato.
- Objeção sem citação não conta.
- Se não achar problema num ângulo, diga "sem objeção" — não invente.
- Você NÃO propõe solução. Você derruba; quem conserta é o planejador.

SAÍDA

## Objeções
| # | Ângulo | Objeção | Fonte | Severidade |
|---|---|---|---|---|

Severidade: BLOQUEIA / IMPORTANTE / RESSALVA

## Veredito
APROVA | APROVA COM RESSALVAS | BLOQUEIA

## Se BLOQUEIA
<o que precisa mudar antes de o plano seguir>
```

---

## Depois do ataque

Volte ao motor original com as objeções. Cada uma recebe **uma** disposição:

| Disposição | Significa |
|---|---|
| **FIXED** | o plano mudou para resolver |
| **ACCEPTED** | risco aceito **com dono nomeado** |

Não existe "vamos ver depois". Risco aceito por ninguém é risco ignorado.

Registre em `docs/consensus-<assunto>.md`, no formato:

```markdown
## Sign-off
Assino que este plano é a coisa certa a construir.
NÃO assino que o código estará correto — isso é a eval.

Assinado por: <nome> · Data: <ISO> · Veredito: canonical
FIXED: <ids>   ACCEPTED: <ids, com donos>
```

---

## Se o adversário cross-family não estiver disponível

Registre isso, não finja que houve consenso:

```markdown
## Limitação
Adversário cross-family não executado — apenas revisão same-family.
Isto é limitação de ferramenta, NÃO aprovação do plano.
```

**"Não conseguiu verificar" ≠ "verificou e aprovou".**
