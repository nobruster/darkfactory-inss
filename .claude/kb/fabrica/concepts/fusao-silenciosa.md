# Fusão silenciosa

O defeito mais perigoso desta fábrica — porque **não gera erro e o total
continua batendo**.

## O que é

Agrupar por um campo que perdeu distinção. Duas categorias diferentes viram uma,
a soma permanece correta, e nenhum gate de valor acusa.

## O caso real: espécie

A fonte trunca todo campo texto em **20 caracteres**. Medido sobre os 65 nomes
oficiais:

```
65 nomes oficiais  →  44 após truncar
13 grupos de colisão · 34 de 65 códigos afetados (52%)
```

O pior grupo, `'Aposentadoria Invali'`, esconde **seis** espécies:

| Código | Espécie | Benefícios |
|---|---|---|
| 32 | Aposentadoria por incapacidade permanente | 3.316.548 |
| 92 | Invalidez Acidente Trabalho | 209.894 |
| 05 | Invalidez Acidentária - Trabalhador Rural | 1.951 |
| 06 | Invalidez Empregador Rural | 391 |
| 33 | Invalidez Aeronauta | 26 |
| 51 | Invalidez Extinto Plano Básico | 25 |

Agrupar por nome somaria **seis políticas públicas distintas** numa linha. O
total continuaria `R$ 78.771.556.568,72` — exatamente certo.

## Por que o gate de soma não pega

```
sum(silver) == sum(bronze)   ✅ passa
count(silver) == count(bronze) ✅ passa
```

Nada se perdeu. Só se **misturou**. Gate de valor mede quantidade, não
identidade.

## O gate que pega

```python
rotulos  = count(distinct especie_rotulo)      # 66
truncados = count(distinct especie_nome_fonte) # 53
assert rotulos > truncados
```

Se alguém reintroduzir o agrupamento por nome, `rotulos` cai para 53 e a
comparação reprova — **sem precisar saber como o erro foi cometido**.

Está em `scripts/eval_doutrina.py`, verificando B-4.

## Onde mais acontece

| Campo | Colisão |
|---|---|
| Banco | `756` (Sicoob) e `748` (Sicredi) → ambos `Banco Cooperativ` |
| Meio de pagamento | `Ccf` e `Ccl` → ambos `Conta-Corrente` |
| Município | código SUIBE de 5 dígitos, nome truncado |

## A regra

**Resolva sempre pelo código, nunca pelo nome.** O código é único por
construção; o nome sobreviveu a um truncamento.

Para exibir, use `especie_rotulo` = `código · nome oficial`. O código vem
primeiro — assim sobrevive a truncamento posterior num BI ou relatório.

## Como reconhecer o risco numa mudança nova

Pergunte: *"esta agregação pode juntar coisas distintas sem que a soma acuse?"*

Se a resposta for talvez, o gate precisa comparar **cardinalidade**, não valor.

Ver: ADR 0003 · `DF-INSS-002` em `contracts/layout.yaml`
