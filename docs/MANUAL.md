# Manual — como operar a Fábrica INSS

**INSS — Benefícios Emitidos** (`D.SDA.PDA.003.EMI`)

> A pergunta que esta fábrica responde:
> **Quanto cada instituição financeira movimenta em benefícios do INSS, por UF?**

Resposta atual: **TOP 4 bancos concentram ~75,8%** de ~R$ 78,5 bi/mês.
É estrutural — varia em centésimos entre competências.

---

## Diferente de uma fábrica nova

Esta fábrica **já está medida e rodando**. Três competências processadas,
contrato v3 congelado, 9 packets `ACEITO` com os gates ligados.

Se você acabou de gerar uma fábrica com `nova-fabrica`, o manual dela está em
`docs/MANUAL.md` **daquele repositório** e cobre o caminho do zero. Este aqui
é sobre **operar** o que já existe.

| Situação | Vá para |
|---|---|
| processar uma competência nova | [Rodar uma competência](#rodar-uma-competência) |
| um gate reprovou | [Quando um gate reprova](#quando-um-gate-reprova) |
| entender o que já rodou | [Ler o estado](#ler-o-estado) |
| mexer no contrato | [Mudar o contrato](#mudar-o-contrato-exige-adr) |

---

## Onde a fábrica fica

```bash
wsl -d Ubuntu-24.04
cd ~/darkfactory-inss
```

⚠️ **No disco Linux, não em `/mnt/c/`.** Bind-mount de arquivo único falha
em `/mnt/c/`, e o I/O é ~10× mais lento. Remote:
`github.com/nobruster/darkfactory-inss`.

Do Git Bash no Windows:

```bash
wsl.exe -d Ubuntu-24.04 -- bash -lc 'cd ~/darkfactory-inss && make status'
```

⚠️ **O bridge Windows→WSL engole `$?` e `$var`.** Um comando com `$c` numa
string aninhada chega vazio, e o código de saída volta sempre `0`. Por isso
`make evals` usa `scripts/rodar_evals.sh`: ele imprime o exit de cada eval.
Para loops, escreva um `.sh` em vez de encadear na linha.

---

## Ler o estado

```bash
make status
```

| Marca | Significa |
|---|---|
| `OK` | `ACEITO` — os gates rodaram e passaram |
| `~?` | `ACEITO_SEM_ANCORA` — **publicou sem juiz de total** |
| `!!` | `REJEITADO` — leia as falhas |

**`~?` não é sucesso.** Significa que aquela competência não tem âncora e
nenhum gate de total rodou. Resolve-se com `make ancora`.

```bash
ls evidence/                    # os packets: a prova do que rodou
make ranking COMP=2026-03       # top 10 bancos da competência
```

> As fábricas geradas por `nova-fabrica` têm um `scripts/estado_contrato.py`
> que resume o estado de medição. Esta não tem: o contrato dela já nasceu
> medido, e a âncora se confere lendo `controle_por_competencia:`.

### Estado em 16/09/2026

| Competência | Linhas | Valor | Âncora |
|---|---|---|---|
| 2026-01 | 41.572.553 | R$ 78.521.752.562,12 | ✅ medida |
| 2026-02 | 41.522.152 | R$ 78.441.374.955,39 | ✅ medida |
| 2026-03 | 41.719.140 | R$ 78.771.556.568,72 | ✅ medida |

Pendentes: 2025-12, 2025-11, 2025-10.

---

## Rodar uma competência

### O caminho curto (competência já ancorada)

```bash
make all COMP=2026-03
make evals COMP=2026-03
```

### O caminho completo (competência nova)

```bash
make fetch  COMP=2025-12     # baixa ~575 MB e congela em 444
make ancora COMP=2025-12     # ~50s varrendo o ZIP — OBRIGATÓRIO
```

Agora registre a âncora em `contracts/layout.yaml`, bloco
`controle_por_competencia:`. Copie os números de
`evidence/_totais-202512.json`:

```yaml
  "2025-12":
    count_linhas: <do arquivo>
    sum_vl_liquido: "<do arquivo>"      # string, não número
    min_vl_liquido: "<do arquivo>"
    max_vl_liquido: "<do arquivo>"
    linhas_invalidas: 0
    medido_em: "<hoje>"
    evidencia: "evidence/_totais-202512.json"
```

⚠️ **`contracts/` é congelado.** Isto exige ADR — ver
[Mudar o contrato](#mudar-o-contrato-exige-adr).

```bash
make all   COMP=2025-12
make evals COMP=2025-12
```

### Por que a âncora é separada

A âncora é medida **antes e independente** do Bronze, direto do ZIP.

> Bronze conferir contra números que o próprio Bronze produziu não é gate —
> é o réu assinando o próprio alvará.

Sem âncora, as camadas publicam `ACEITO_SEM_ANCORA`. Até 16/09/2026 elas
publicavam `ACEITO` com o gate desligado, e **82 milhões de linhas foram
publicadas sem que nada as tivesse conferido**. Ver
[ADR 0006](adrs/0006-auditoria-por-tres-modelos.md).

Tempo: fetch ~2 min · ancora ~50s · bronze ~2 min · silver ~1 min · gold <1s.

---

## Quando um gate reprova

**Gate reprovado = ZERO artefato.** Nada parcial fica no disco. Isso é
correto: um Parquet pela metade é pior que nenhum.

### A regra que resolve a maioria

> Quando o resultado diverge do contrato, **classifique** — não conserte o
> contrato.

| Código | Quando |
|---|---|
| `CONFIRMED_SOURCE_DEFECT` | a fonte mentiu, e dá para provar |
| `MODERN_DEFECT` | a fábrica errou — é nosso, conserta-se |
| `CONTRACT_AMBIGUITY` | discordam sem que um esteja errado |
| `UNRESOLVED` | não se sabe ainda. É resposta legítima. |

⚠️ **O erro nº 1** é virar vermelho em verde mexendo na expectativa.
Reescrever o juiz é trapaça, não conserto.

### Sintomas

| Mensagem | Causa provável |
|---|---|
| `soma X != âncora Y` | **NÃO ajuste.** A fonte mudou ou o parsing quebrou |
| `count X != âncora Y` | idem — compare com `evidence/_totais-*.json` |
| `rejeicoes=N (contrato exige 0)` | linha fora das 14 colunas. Investigue |
| `coluna monetária não-DECIMAL` | faltou `cast` depois de um `avg()` |
| `agregação por nome? códigos <= nomes` | alguém trocou a chave do Gold |
| `mun_residencia_codigo com >1 nome` | o código deixou de ser chave |
| `B-7: pasta congelada alterada` | há mudança não commitada em `contracts/` |
| `B-7c: congelado mas gravável` | falta `chmod 444` |
| `cercas divergem` | `settings.json` e `.cvg/gate.yaml` discordam |

### Verificar a integridade

```bash
cd contracts && sha256sum -c CHECKSUMS.txt && cd ..
make cercas
make conferir COMP=2026-03    # confere o Bronze publicado contra a âncora
```

---

## Mudar o contrato (exige ADR)

`contracts/` · `_raw/` · `docs/adrs/` · `evidence/` são **congelados**:
chmod 444, sha256 registrado, protegidos por duas cercas e pelo CI.

```bash
# 1. escreva o ADR que justifica — e que NOMEIE o arquivo que vai mudar
$EDITOR docs/adrs/0007-minha-decisao.md

# 2. destrave, edite, recongele
chmod 644 contracts/layout.yaml
$EDITOR contracts/layout.yaml
python3 scripts/refrescar_checksums.py --confirmo-que-existe-adr

# 3. prove que nada quebrou
make qa
make evals COMP=2026-03
```

⚠️ **O CI bloqueia PR que mexa em `contracts/` sem ADR novo que cite o
arquivo pelo nome.** Um ADR sobre outro assunto não é autorização.

⚠️ **ADR aceito não se edita — supersede-se com ADR novo.** Editar apaga o
registro de que a decisão anterior existiu. O CI também bloqueia isso.

---

## Qualidade

```bash
make qa                      # lint + testes + skills + cercas (sem dados)
make evals COMP=2026-03      # as 3 evals (exigem lakehouse)
bash scripts/rodar_evals_todas.sh 2026-01 2026-02 2026-03
```

| Eval | Prova |
|---|---|
| `eval-1` packets | os 3 packets saem `ACEITO`, sem gate de âncora falso |
| `eval-2` coerência | o total é idêntico nas 3 camadas |
| `eval-3` doutrina | espécie por código, sentinelas fora do ranking, 27 UFs, congelados íntegros |

### Prove que o gate reprova

Um gate que nunca se viu reprovar é decoração. Adultere a âncora em **um
centavo** e rode `make silver` — ele deve reprovar. Depois desfaça.

Leva dois minutos e vale mais que ler o código.

---

## Os 5 defeitos catalogados

| ID | Defeito | Tratamento |
|---|---|---|
| `DF-INSS-001` | `Espécie` aparece 2× no cabeçalho | leitura **posicional** |
| `DF-INSS-002` | truncamento em 20 chars funde 34 de 65 códigos | join pelo **código** |
| `DF-INSS-003` | código 67 na fonte, fora do dicionário | complemento separado |
| `DF-INSS-004` | fonte × dicionário divergem em 29 códigos | ambas preservadas |
| `DF-INSS-005` | duas UFs por registro (município × beneficiário) | fatos distintos |

### Por que o DF-INSS-002 importa

`'Aposentadoria Invali'` esconde **seis** espécies distintas. Agrupar por nome
somaria seis políticas públicas numa linha — **e o total continuaria certo**.
Nada acusaria.

O mesmo com bancos: `756` (Sicoob) e `748` (Sicredi) viram `Banco Cooperativ`;
`037` e `047` viram `Banco do Estado`.

### A armadilha inversa (DF-INSS-005)

Uma auditoria apontou que 5.563 de 5.572 códigos de município aparecem em mais
de uma UF — logo o código não seria chave. **Medido: era chave perfeita**
(5.572 ↔ 5.572). A outra UF era um segundo fato: `uf_residencia` é do
beneficiário, a UF no nome é do município.

A chave "corrigida" `(uf, codigo)` teria partido São Paulo em 27 municípios —
**e o total continuaria batendo**.

> **Objeção de auditoria é hipótese, não veredito. Meça antes de corrigir.**

---

## O Hermes

Bot Telegram `@factory_inss_bot`, job `fabrica-inss-vigia`, avisa às 9h e 21h.

> ⚠️ **Ele NUNCA processa sem autorização explícita.** Vigia, avisa, espera.

SOUL em `C:\Users\nobru\AppData\Local\hermes\SOUL.md`.
Ao mudar o SOUL: reiniciar o gateway **e apagar a sessão**
(`hermes sessions delete <id> --yes`) — senão ele mantém o contexto antigo.

⚠️ **Divergência a resolver:** `docs/OPERADOR.md` descreve degrau 2 ("executa
e reporta"); o `CLAUDE.md` e a regra acima dizem degrau 1 (vigia e espera).
A prática em vigor é a **degrau 1**. O `OPERADOR.md` está desatualizado.

---

## O que nunca fazer

- **Não** editar packet em `evidence/`. Packet errado se **reexecuta**.
- **Não** editar ADR aceito. **ADR novo que supersede.**
- **Não** ajustar o contrato para um teste passar.
- **Não** "corrigir" dado errado da fonte. Classifique.
- **Não** desligar gate para destravar. Se reprova, está funcionando.
- **Não** marcar âncora sem ter medido com `make ancora`.
- **Não** rodar `make clean CONFIRM=clean-runtime` sem saber: apaga o runtime.

---

## Para entender *por que*

- [`../CLAUDE.md`](../CLAUDE.md) — doutrina e contexto
- [`adrs/0006`](adrs/0006-auditoria-por-tres-modelos.md) — **a auditoria**:
  como 82 milhões de linhas foram publicadas com `ACEITO` sem conferência,
  e qual das nove objeções estava errada
- [`adrs/0002`](adrs/0002-decimal-nunca-float.md) — dinheiro é DECIMAL
- [`adrs/0005`](adrs/0005-inss-direto-fora-do-ranking.md) — o INSS não é banco
