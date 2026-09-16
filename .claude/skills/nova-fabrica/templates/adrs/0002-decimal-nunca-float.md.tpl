# ADR 0002 — Dinheiro é DECIMAL, nunca float

- Status: Accepted. Vinculante.
- Data: {{DATA}}
- Decisor: Bruno (owner)
- Origem: **semente** gerada por `nova-fabrica`, herdada do `darkfactory-inss`
- Colunas afetadas nesta fábrica: `{{COLUNAS_MONETARIAS}}`

## Contexto

`0.1 + 0.2 != 0.3` em ponto flutuante. Sobre 40 milhões de linhas, o erro não
fica na sexta casa: ele se acumula e aparece no total.

Pior: o defeito fica no **tipo**, não no valor. Uma coluna que virou `DOUBLE`
continua somando quase certo, e o gate de soma continua passando — até que
alguém compare com a fonte e ache uma diferença de centavos que ninguém sabe
explicar.

O caso concreto que motivou isto: no INSS, `vl_medio` era publicado como
`DOUBLE` porque

```sql
avg(vl_liquido)   -- DuckDB devolve DOUBLE mesmo sobre DECIMAL
```

A soma batia. A média era float. Só apareceu numa auditoria que olhou o
`information_schema`, não os números.

## Decisão

Toda coluna monetária é `DECIMAL(18,2)` — no Bronze, no Silver e no Gold.

**Conversão explícita após qualquer agregação que possa promover o tipo:**

```sql
cast(round(avg(valor), 2) as decimal(18,2))   as valor_medio
```

**Gate no Gold** que varre `information_schema.columns` e reprova qualquer
coluna monetária cujo `data_type` não comece com `DECIMAL`. O gate existe
porque o olho não pega: o número impresso parece igual.

Nos packets de evidência, valores monetários são gravados como **string**.
`json.dump` de um `Decimal` viraria float e perderia o centavo na serialização.

## Consequências

- Comparações são exatas: `str(soma) == ancora["sum_..."]`, sem tolerância.
- Tolerância **zero** é possível. Com float, seria preciso inventar um épsilon
  — e todo épsilon é uma licença para errar um pouquinho.
- Divisões precisam de cuidado: `round(x, 2)` antes do cast, sempre.

## Alternativa rejeitada

*Usar float com tolerância de 1 centavo.* Funciona até a fonte ter um defeito
real de 1 centavo — e aí a fábrica não consegue distinguir o defeito da sua
própria imprecisão. O método inteiro depende de preservar o defeito; uma banda
de tolerância o apaga.
