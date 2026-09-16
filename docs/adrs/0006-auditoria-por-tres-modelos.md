# ADR 0006 — A âncora é por competência, e todo gate desligado é visível

- Status: Accepted. Vinculante.
- Data: 2026-09-16
- Decisor: Bruno (owner)
- Supersede: nada. Estende `0002`, `0003` e `0005`.
- Arquivos congelados alterados: `layout.yaml`, `CHECKSUMS.txt`
- Evidência: `evidence/_totais-202602.json` · `evidence/_totais-202603.json`

## Contexto

Em 16/09/2026 a estrutura da fábrica foi auditada por três modelos
independentes (Opus, Sonnet, Haiku), sem acesso ao raciocínio uns dos outros.
Nove objeções bloqueantes. O achado que as une, nas palavras do relatório:

> *a fábrica olha para espécie com microscópio e para o resto não olha.*

A disciplina construída em torno de `DF-INSS-001..004` era real. O problema é
que ela não tinha sido aplicada a mais nada — e a aparência de rigor num lugar
foi lida como rigor em todos.

**A objeção mais grave (#28).** Bronze, Silver e Gold desligavam os gates de
total quando a competência não era a declarada no contrato:

```python
confere_controle = comp == contrato["competencia"]
if confere_controle:
    ...   # só aqui os totais eram conferidos
```

Em 2 das 3 competências processadas o juiz estava desligado. E o packet
continuava dizendo `"status": "ACEITO"`, com `"count_confere": false` escondido
lá dentro. **82 milhões de linhas e R$ 157 bilhões publicados sem que nada
jamais os tivesse conferido contra a fonte.**

Ninguém mentiu deliberadamente. O `false` estava lá, honesto, no campo certo.
Mas quem lê um packet lê o `status` — e o `status` dizia que estava tudo bem.

## Decisão

**1. A âncora é por competência.** `controle_por_competencia:` no contrato
guarda count, soma, mínimo e máximo de cada competência, medidos por
`scripts/totais_controle.py` varrendo o ZIP congelado — antes e independente
do Bronze. Bronze conferir contra si mesmo não é gate: é o réu assinando o
próprio alvará.

**2. Gate que não roda não passa por gate que passou.** Sem âncora, a camada
publica como `ACEITO_SEM_ANCORA`, não como `ACEITO`. É um estado visível.
`eval_packets` reprova qualquer packet `ACEITO` que tenha um gate `false`.

**3. O Gold confere contra a fonte, não só contra o Silver.** Coerência entre
camadas adjacentes não prova nada sobre a origem: três camadas podem errar
junto e bater entre si.

Correções que acompanham (todas verificadas por medição antes de aplicar):

| # | Objeção | Disposição |
|---|---|---|
| 3 | `037/047 Banco do Estado` colidem, fora do contrato | catalogado — 111.970 linhas |
| 4 | código de município não seria único | **REFUTADO** — ver abaixo |
| 5 | `996` ranqueado como banco | sentinela, como o `998` (ADR 0005 por classe) |
| 7 | eval B-4 validava coluna que o próprio Silver constrói | passa a observar o Gold |
| 8 | B-7 usava `git status`, cego a `_raw/*.zip` | sha256 + permissão |
| 9 | CI dizia cobrir `docs/adrs/` e não cobria | ADR existente não se edita; ADR novo precisa nomear o arquivo |
| 10 | `settings.json` e `gate.yaml` discordavam | `scripts/verificar_cercas.py` |
| 11 | `evidence/*-run.json` casava com zero arquivo | `evidence/**` |
| 14 | faixa de jan/2026 generalizada | renomeada `faixa_observada_2026_01` |

## A objeção que foi refutada

A #4 dizia: *"5.563 dos 5.572 códigos de município aparecem em mais de uma UF —
o código não é chave, use (uf, codigo)."* O número estava certo. A conclusão,
invertida.

Medido: **5.572 códigos ↔ 5.572 nomes, zero colisão nos dois sentidos.** O
código É chave. O que acontece é que `mun_residencia` traz a UF do **município**
(`21504-Sp-São Paulo`) e `uf_residencia` traz a UF do **beneficiário** — e há
429.803 linhas, numa amostra de 7 UFs, em que as duas divergem legitimamente.

A chave "corrigida" `(uf_residencia, codigo)` teria partido São Paulo em 27
municípios — **e o total continuaria batendo**. Fusão silenciosa ao inverso,
por fragmentação, introduzida em nome de uma auditoria.

Isto fica registrado porque é a lição mais cara do dia: **uma objeção de
auditoria é hipótese, não veredito.** Sete das nove foram confirmadas por
medição. Esta foi medida também — e o dado disse não.

## Consequências

- Uma competência nova exige medir a âncora antes de publicar como `ACEITO`.
  É uma varredura de ~50s sobre 41M linhas. É o preço de ter juiz.
- Os 6 packets que diziam `ACEITO` com gate `false` foram **regerados**, não
  editados. Editar evidência falsifica histórico; reexecutar produz evidência
  nova, e as duas ficam no git.
- `faixa_observada` deixou de existir como nome genérico. Nenhum gate testa
  faixa hoje: um valor absurdo passaria. Fica registrado como lacuna conhecida,
  não como problema resolvido.

## Alternativa rejeitada

*Ajustar `competencia:` no contrato a cada execução.* Faria o gate rodar — mas
com um contrato que muda de identidade conforme o que se processa. O juiz
passaria a ser função do réu.
