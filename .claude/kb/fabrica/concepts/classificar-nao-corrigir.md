# Classificar, não corrigir

A regra que mais gera desconforto — e a que sustenta todas as outras.

## O caso que nomeia tudo

Um arquivo de liquidação declara no rodapé `173,44`. As linhas somam `173,45`.

Três reações instintivas, todas erradas:

| Reação | Por que falha |
|---|---|
| "corrige pro valor certo" | esconde que a origem tem defeito |
| "usa o que o rodapé diz" | processa dinheiro errado, sabendo |
| "ignora e processa" | o erro entra e contamina tudo depois |

A resposta do método:

> **Preserva a declaração. Recusa o lote. Classifica o defeito. Não conserta.**

## Por que preservar é melhor que corrigir

Quem mandou o arquivo errado **fica sabendo**. Se você conserta em silêncio, o
defeito continua na origem, gerando arquivos errados indefinidamente — e um dia
a diferença não vai ser um centavo.

A frase que resume, de uma analista fictícia do caso original:

> *"Se sua planta nova escrever 173,45 no rodapé em silêncio, não teremos nada
> para mostrar à origem."*

**Corrigir destrói a evidência.**

## Como isso aparece nesta fábrica

O código de espécie **67** (`Pecúlio Obrigatório`) existe na fonte e não no
dicionário oficial do INSS:

```
2026-01   0 linhas
2026-02   3 linhas   R$ 3.243,00
2026-03   6 linhas   R$ 7.863,00
```

Recorrente e crescendo. Seria trivial adicionar uma linha no
`especies-oficial.xlsx` e "resolver" — 6 linhas em 41,7 milhões.

**Recusamos.** O arquivo deixaria de ser o publicado pelo INSS, o checksum
quebraria, e perderíamos a prova de que o INSS não documenta esse código.

A saída foi `contracts/especies-complemento.yaml`, separado, com
`especie_nome_origem` marcando a procedência:

```
dicionario_oficial   65 códigos · 41.719.134 linhas
fonte                 1 código  ·          6 linhas
```

A ambiguidade **continua aberta** e escalada ao INSS. O complemento documenta,
não resolve.

## As classificações

| Código | Quem errou | O que fazer |
|---|---|---|
| `CONFIRMED_SOURCE_DEFECT` | a origem | preserva o número, recusa o lote |
| `MODERN_DEFECT` | nossa fábrica | **conserta a fábrica, nunca a expectativa** |
| `CONTRACT_AMBIGUITY` | o contrato não decide | escala, **não chuta** |
| `UNRESOLVED` | não classificado | não pode ser servido |

## A tentação que o método proíbe

Quando um gate reprova, existe sempre um caminho rápido:

```python
# NÃO
if abs(soma_a - soma_b) < Decimal("0.01"):   # tolerância
    return True
```

Com tolerância de 1 centavo, o `DF-INSS-001` passaria como válido. **A mentira
viraria ruído aceitável.**

> **O gate que reprova está fazendo o trabalho dele.** Quando alguém propõe
> afrouxá-lo para destravar, esse é o achado — não o obstáculo.

## Como saber se você está corrigindo em silêncio

Pergunte: *"depois desta mudança, alguém consegue provar que a origem tem um
problema?"*

Se a resposta for não, você apagou evidência.

Ver: ADR 0004 · `DF-INSS-003` · `contracts/especies-complemento.yaml`
