# ADR 0001 — Leitura por posição, nunca por nome de cabeçalho

- Status: Accepted. Vinculante.
- Data: {{DATA}}
- Decisor: Bruno (owner)
- Origem: **semente** gerada por `nova-fabrica`, herdada do `darkfactory-inss`

## Contexto

Esta é uma decisão tomada **antes** de medir a fonte de {{DISPLAY_NAME}}. Ela
vem de um caso real e vale por precaução até que a medição a confirme ou a
contradiga.

No dataset do INSS, o cabeçalho traz a coluna `Espécie` **duas vezes** —
posições 12 e 13. Uma é o código, a outra é o nome truncado. Testado:

```python
csv.DictReader(...)   # mantém a pos 13 e PERDE a 12 — que é o código
```

Sem erro. Sem aviso. O código simplesmente não existe no dicionário que volta,
e todo o resto do pipeline passa a trabalhar com o nome truncado — que funde
categorias distintas.

Um cabeçalho duplicado não é exótico: acontece em qualquer extração que
concatene campos de sistemas diferentes.

## Decisão

Ler **por posição**, sempre. O contrato declara `colunas[]` com `pos`, `nome`
e `origem`; o parser nunca consulta o cabeçalho para decidir o que é o quê.

O cabeçalho serve para **conferir** que a fonte não mudou de layout — nunca
para endereçar campo.

## Consequências

- `make perfil` compara o cabeçalho real com o contrato e reclama se divergir.
- Uma coluna nova no meio da fonte **quebra o gate**, em vez de deslocar
  silenciosamente todos os campos seguintes.
- O contrato fica mais verboso: cada coluna precisa de `pos` explícito. É o
  preço de não depender de um nome que a fonte pode repetir.

## Se esta fonte não tiver o problema

Mantenha a decisão mesmo assim. Ler por posição num arquivo de cabeçalho
limpo custa nada; ler por nome num arquivo que **um dia** ganhe duplicata
custa uma investigação inteira.

Se decidir o contrário, **supersede com ADR novo** — não edite este.
