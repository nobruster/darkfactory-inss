---
name: nova-fabrica
description: |
  Gera uma Dark Factory completa para uma fonte de dados nova — Makefile,
  ingestão, medalhão Bronze/Silver/Gold, contrato, evals, agentes, CI e ADRs
  semente. A fábrica nasce com o contrato marcado NAO_MEDIDO e os gates
  RECUSANDO build até que os números venham de medição real.

  Use quando: aparecer uma demanda nova (outro dataset do INSS, Receita,
  IBGE, SUS, um CSV de cliente) e você quiser a mesma disciplina do dia 1,
  sem copiar-colar o projeto INSS e esquecer de trocar algum número.
---

# nova-fabrica — gerador de fábricas

Uma demanda nova chega. Em vez de copiar o `darkfactory-inss` e caçar os
números de janeiro esquecidos no contrato, você responde um formulário curto
e sai uma fábrica que **se recusa a construir** enquanto ninguém mediu a fonte.

## Por que gerar em vez de copiar

Copiar um projeto que funciona é a forma mais rápida de propagar suas mentiras.
O `darkfactory-inss` tem `count_linhas: 41572553` no contrato. Copiado para
outra fonte, esse número continua lá — e o gate compara contra ele. Uma de duas
coisas acontece:

1. o gate reprova sempre, e alguém o desliga para "destravar"; ou
2. alguém troca o número por um palpite, e o juiz vira decoração.

Foi exatamente o segundo caminho que a auditoria de 16/09/2026 encontrou no
INSS — [ADR 0006](../../../docs/adrs/0006-auditoria-por-tres-modelos.md). A
fábrica publicava `ACEITO` com o gate desligado.

**Gerando, o contrato nasce vazio e honesto.** `NAO_MEDIDO` não é placeholder
a preencher depois: é um estado que faz `make bronze` sair com erro.

---

## Uso

```bash
# 1. descrever a demanda
$EDITOR .claude/skills/nova-fabrica/menu/fabricas.yaml

# 2. gerar
bash .claude/skills/nova-fabrica/scaffold.sh receita-cnpj

# 3. entrar e medir — o contrato só ganha número aqui
cd ~/darkfactory-receita-cnpj
make init
make fetch
make perfil          # varre a fonte; escreve evidence/_perfil-*.json
make ancora          # mede count e soma direto da fonte congelada
make contrato        # transfere o medido para o contrato (pede confirmação)

# 4. agora sim
make all
```

**Entre o passo 2 e o 4 a fábrica não constrói.** É de propósito.

---

## O que é gerado

```text
~/darkfactory-<slug>/
├── Makefile                    alvos iguais aos do INSS: all, perfil, ancora, qa, evals
├── contracts/
│   ├── layout.yaml             ← NAO_MEDIDO. O juiz, ainda sem números.
│   └── CHECKSUMS.txt           vazio até a primeira fonte congelar
├── ingestion/
│   ├── fetch_fonte.py          baixa, congela 444, grava sha256
│   └── ingest_bronze.py        fonte → Parquet, gates de rejeição e total
├── scripts/
│   ├── perfil_cobertura.py     mede domínios e cobertura
│   ├── totais_controle.py      mede a ÂNCORA (count, soma, min, max)
│   ├── build_silver.py         conformação + gates
│   ├── build_gold.py           agregação + gates
│   ├── eval_packets.py         os packets saem ACEITO e publicados
│   ├── eval_coerencia.py       o total é idêntico nas 3 camadas
│   ├── eval_doutrina.py        congelados intactos, sha256, chmod 444
│   ├── verificar_cercas.py     settings.json e gate.yaml concordam
│   └── refrescar_checksums.py  única via sancionada de mexer no checksum
├── docs/adrs/
│   ├── 0001-leitura-posicional.md      semente — adapte ou supersede
│   ├── 0002-decimal-nunca-float.md     semente
│   └── 0003-ancora-por-competencia.md  semente (a lição do INSS)
├── .claude/
│   ├── settings.json           deny-list espelhando gate.yaml
│   ├── agents/                 fabrica-architect, fabrica-reviewer
│   └── skills/novo-agente/     o gerador de agentes, já instalado
├── .cvg/gate.yaml              cerca de escrita
├── .github/workflows/          lint, testes, contrato, congelado, cercas
├── tests/
│   ├── test_ancora.py          a âncora existe e nenhum ACEITO esconde gate false
│   └── test_contrato.py        o contrato não pode estar NAO_MEDIDO num build
├── evidence/                   vazio; os packets nascem aqui
├── CLAUDE.md                   contexto do projeto para a próxima sessão
└── README.md
```

---

## O que a fábrica gerada já sabe

Sem você escrever nada:

| Herdado | O quê |
|---|---|
| **Doutrina** | "Sem juiz, não se constrói. Preserve o defeito. Recuse o lote. Verde pelo motivo certo." |
| **Âncora por competência** | o gate de total **nunca** se desliga sozinho; sem âncora publica `ACEITO_SEM_ANCORA` |
| **Publicação atômica** | `.parcial` + `rename`; gate reprovado = ZERO artefato |
| **Decimal nunca float** | dinheiro é `DECIMAL`, e há gate que acusa `avg()` devolvendo `DOUBLE` |
| **Pastas congeladas** | `_raw/`, `contracts/`, `docs/adrs/` — chmod 444 + sha256 + CI |
| **Duas cercas** | `settings.json` e `.cvg/gate.yaml`, com script que exige que concordem |
| **Classificação** | `CONFIRMED_SOURCE_DEFECT` · `MODERN_DEFECT` · `CONTRACT_AMBIGUITY` · `UNRESOLVED` |
| **Evidência não se edita** | packet errado se **reexecuta**; conferência retroativa vira arquivo novo |

---

## Anatomia de uma entrada de menu

```yaml
receita-cnpj:
  display_name: "Receita Federal — Cadastro CNPJ"
  pergunta: "Quantas empresas abrem e fecham por município, por mês?"
  # ↑ a pergunta que o Gold responde. Sem ela não há Gold: há dump.

  fonte:
    url_padrao: "https://arquivos.receitafederal.gov.br/.../Empresas{n}.zip"
    formato: csv                # csv | parquet | json | fixed-width
    encoding: latin-1           # NUNCA assuma utf-8 sem medir
    separador: ";"
    tem_cabecalho: false
    particao: "competencia"     # como a fonte se divide: competencia | uf | lote

  grao_silver: ["cnpj_basico"]
  grao_gold: ["competencia", "municipio_codigo", "situacao"]

  colunas_monetarias: ["capital_social"]
  # ↑ viram DECIMAL(18,2) e ganham gate anti-float automático

  chaves_suspeitas: ["municipio_codigo"]
  # ↑ o gerador cria gate que prova bijeção código↔nome (lição DF-INSS-005)

  sentinelas:
    "0000000": "CNPJ não informado"
  # ↑ viram categoria própria no Gold, nunca excluídas nem imputadas
```

Campos obrigatórios: `display_name`, `pergunta`, `fonte.url_padrao`,
`fonte.formato`, `grao_gold`. O resto tem padrão seguro.

---

## O que este gerador NÃO faz

- **Não mede a fonte.** Ele escreve `NAO_MEDIDO` e o Makefile te manda medir.
  Foi decisão deliberada: contrato que nasce de medição que ninguém viu
  acontecer é palpite com aparência de âncora.
- **Não adivinha o layout das colunas.** `make perfil` lê o cabeçalho real e
  propõe; você confirma. O gerador não inventa nome de campo.
- **Não escreve o Gold.** Ele gera o esqueleto com o grão declarado e os gates.
  A regra de negócio — o que a agregação significa — é sua.
- **Não cria ADR por você.** Gera três sementes com o raciocínio do INSS.
  Se a fonte nova discordar de alguma, **supersede com ADR novo** — não edite.

---

## Manutenção

```bash
# a doutrina evoluiu no INSS? veja o que mudaria numa fábrica gerada
bash .claude/skills/nova-fabrica/scaffold.sh --diff receita-cnpj

# verificar a skill (roda antes de gerar qualquer coisa)
bash .claude/skills/nova-fabrica/quality-gate.sh --strict
```

⚠️ **`--diff` mostra, não aplica.** Propagar doutrina para uma fábrica que já
tem contrato medido e evidência publicada é decisão com ADR, não `sed`.

---

## A regra que justifica tudo isto

> Uma fábrica que não recusa nada não é fábrica: é um script com pastas
> bonitas. O primeiro gate que a fábrica gerada executa é contra **ela mesma**
> — o contrato `NAO_MEDIDO`.
