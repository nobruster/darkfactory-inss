# Workflow: competência nova

O fluxo mais comum da fábrica. Do aviso do Hermes ao Gold publicado.

**Quando:** o INSS publicou uma competência que ainda não processamos.
**Quem dispara:** o Hermes às 9h ou 21h, ou você pedindo.
**Duração:** ~6 min (download 2 + bronze 2 + silver 0,5 + gold 0,1).

---

## O fluxo

```text
1. Hermes avisa      "3 pendentes: 2025-12, 2025-11, 2025-10"
                     ⚠️ ele NÃO processa sem sua autorização
2. Você autoriza     "processa 2025-12"
3. make all          fetch → bronze → silver → gold
4. Gates             15 verificações, tolerância zero
5. Packet            evidence/<camada>-<AAAAMM>.json
6. Você confere      make status · make ranking
```

---

## Passo a passo

```bash
cd ~/darkfactory-inss

# 1. o que falta
.venv/bin/python scripts/operador.py pendentes

# 2. rodar (a fonte não é rebaixada se já existir)
make all COMP=2025-12

# 3. conferir
make status
make ranking COMP=2025-12

# 4. provar
make evals COMP=2025-12
```

---

## O que pode acontecer

### Tudo verde

```
BRONZE ACEITO · 41.xxx.xxx linhas
SILVER ACEITO · soma confere com Bronze
GOLD ACEITO   · 27 UFs · INSS-direto fora do ranking
```

Commitar os packets. São a prova do que rodou.

### Espécie órfã

```
DF-INSS-003 : órfãos ['73'] · N linhas · CONTRACT_AMBIGUITY
```

**Não é falha.** A fábrica classificou e seguiu. Decisão sua:

| Ocorrência | O que fazer |
|---|---|
| primeira vez, poucas linhas | deixar como ambiguidade aberta |
| recorrente em 2+ competências | avaliar complemento (ver ADR 0004) |
| **nunca** | inventar descrição pelo nome truncado |

### Um gate reprova

```
SILVER REJEITADO — nada publicado
  - soma silver X != bronze Y
```

**Pare.** Não afrouxe o gate. Ordem de investigação:

1. o packet do Bronze bate com a fonte?
2. mudou algo no contrato desde a última competência?
3. é defeito da fonte (classifica) ou nosso (`MODERN_DEFECT`, conserta)?

Se não souber em 15 minutos, escale. Tentar de novo sem entender esconde o
defeito.

### Fonte mudou no servidor

```bash
make check COMP=2025-12     # HEAD, sem baixar
```

Se o tamanho divergir do registrado: **investigue antes de rebaixar**. Pode ser
republicação com correção — o que muda os totais de controle.

---

## Não faça

| | Por quê |
|---|---|
| processar tudo de uma vez | ~580 MB e 6 min cada; erro numa esconde erro na outra |
| pular `make evals` | o packet diz que passou; a eval **prova** |
| rebaixar fonte que já existe | `--force` só com motivo; o sha é a cadeia de custódia |
| commitar com gate vermelho | o packet vira registro de que aceitamos o errado |

---

Ver: [`tasks/T-20260915-processar-competencia.md`](../../tasks/T-20260915-processar-competencia.md)
