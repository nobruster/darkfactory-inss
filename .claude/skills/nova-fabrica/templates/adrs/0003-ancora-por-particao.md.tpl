# ADR 0003 — A âncora é por partição, e gate desligado é visível

- Status: Accepted. Vinculante.
- Data: {{DATA}}
- Decisor: Bruno (owner)
- Origem: **semente** gerada por `nova-fabrica`, herdada do `darkfactory-inss`
- Partição desta fábrica: `{{PARTICAO}}`

## Contexto

Este ADR existe por causa de um defeito encontrado no projeto INSS em
16/09/2026, numa auditoria por três modelos independentes. Foi a objeção mais
grave das nove, e é o tipo de defeito que uma fábrica nova repete de graça se
ninguém avisar.

O código era este, e parece razoável:

```python
confere_controle = comp == contrato["competencia"]
if confere_controle:
    if total != ctl["count_linhas"]:
        falhas.append(...)      # só aqui os totais eram conferidos
```

O contrato declarava **uma** competência. Ao processar qualquer outra, o gate
de total simplesmente não rodava. E o packet continuava dizendo:

```json
{
  "status": "ACEITO",
  "gates": { "count_confere": false, "soma_confere": false }
}
```

Ninguém mentiu. O `false` estava lá, no campo certo, honesto. Mas quem lê um
packet lê o `status` — e o `status` dizia que estava tudo bem.

**Resultado: 82 milhões de linhas e R$ 157 bilhões publicados sem que nada
jamais os tivesse conferido contra a fonte.** Os dados estavam corretos — a
conferência retroativa provou. Mas isso foi sorte, não processo: ninguém
sabia, porque não havia prova.

## Decisão

**1. A âncora é por partição.** `controle_por_particao:` no contrato guarda
count, soma, mínimo e máximo de **cada** partição, medidos por
`scripts/totais_controle.py` varrendo a fonte congelada — antes e
independente do Bronze.

> Bronze conferir contra si mesmo não é gate: é o réu assinando o próprio
> alvará.

**2. Gate que não rodou não passa por gate que passou.** Sem âncora, a camada
publica como `ACEITO_SEM_ANCORA`, nunca `ACEITO`. É um estado visível, com
marca própria no `make status`. `eval_packets` reprova qualquer packet
`ACEITO` que tenha um gate de âncora `false`.

**3. O Gold confere contra a fonte, não só contra a camada anterior.**
Coerência entre camadas adjacentes não prova nada sobre a origem: três
camadas podem errar junto e bater perfeitamente entre si.

**4. O contrato nasce `NAO_MEDIDO` e a fábrica recusa construir.** Um número
que ninguém viu ser medido é indistinguível de um palpite.

## Consequências

- Partição nova exige medir a âncora antes de publicar como `ACEITO`. É uma
  varredura de cerca de um minuto. É o preço de ter juiz.
- Os arquivos `evidence/_totais-*.json` **não são descartáveis**: o contrato
  os cita como evidência, e contrato que aponta para arquivo fora do git não
  prova nada. O `.gitignore` tem exceção explícita para eles.
- Packet errado se **reexecuta**, nunca se edita. Conferência retroativa vira
  arquivo **novo**, ao lado do antigo. Os dois ficam no histórico.

## Alternativa rejeitada

*Ajustar a partição declarada no contrato a cada execução.* Faria o gate
rodar — mas com um contrato que muda de identidade conforme o que se
processa. O juiz passaria a ser função do réu.

## A lição que generaliza

O defeito não era um bug: era uma linha de código razoável que desligava o
juiz sem avisar. Não havia teste que o pegasse, porque o pipeline **passava**.

Por isso `tests/test_ancora.py` testa a **estrutura**, não a execução: que
toda partição processada tenha âncora, e que nenhum packet publicado diga
`ACEITO` escondendo um gate falso.

> Um gate que nunca se viu reprovar é decoração. Prove que o seu reprova —
> adultere a âncora em um centavo e veja o vermelho.
