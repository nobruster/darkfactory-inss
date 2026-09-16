# Contrato — {{DISPLAY_NAME}}
#
# ESTE ARQUIVO É O JUIZ. Quando o código e este contrato discordarem,
# o contrato decide quem está errado.
#
# ⚠ NUNCA ajuste este arquivo para fazer um teste passar. Reescrever o juiz
#   é trapaça, não conserto. Quando o resultado diverge, CLASSIFICA-SE.
#
# Gerado por nova-fabrica em {{DATA}}. Nenhum número aqui foi medido ainda.

version: 1
dataset: {{SLUG}}
pergunta: "{{PERGUNTA}}"
gerado_em: "{{DATA}}"

# ═════════════════════════════════════════════════════════════
# ESTADO DO CONTRATO — leia antes de tudo
# ═════════════════════════════════════════════════════════════
# Enquanto `medido` for false, a fábrica RECUSA construir. Não é um aviso:
# ingest_bronze.py sai com erro e nenhum Parquet é escrito.
#
# Para medir:
#     make fetch                  # baixa e congela a fonte
#     make perfil                 # varre e escreve evidence/_perfil-*.json
#     make contrato               # transfere o medido para cá (pede confirmação)
#
# Por que não deixar o gerador medir sozinho: um contrato que nasce de uma
# medição que ninguém viu acontecer é palpite com aparência de âncora. O custo
# de ~1 minuto de varredura compra a diferença entre juiz e decoração.
medido: false
estado: NAO_MEDIDO

# ═════════════════════════════════════════════════════════════
# FONTE
# ═════════════════════════════════════════════════════════════
fonte:
  url_padrao: "{{URL_PADRAO}}"
  formato: {{FORMATO}}
  particao: {{PARTICAO}}

  # ⚠ Os quatro campos abaixo são DECLARADOS, não medidos. `make perfil`
  #   confere cada um contra os bytes reais e reclama se divergir.
  #   Encoding errado não estoura: ele corrompe acento em silêncio.
  encoding: {{ENCODING}}
  separador: "{{SEPARADOR}}"
  cabecalho: {{TEM_CABECALHO}}
  leitura: {{LEITURA}}

  # NAO_MEDIDO até `make perfil`
  zip_bytes: null
  zip_sha256: null
  arquivo_bytes: null
  colunas: null
  terminador: null

# ═════════════════════════════════════════════════════════════
# TOTAIS DE CONTROLE — a âncora de integridade
# ═════════════════════════════════════════════════════════════
# A âncora é POR PARTIÇÃO ({{PARTICAO}}), medida direto da fonte congelada
# por scripts/totais_controle.py — ANTES e INDEPENDENTE do Bronze.
#
# Bronze conferir contra si mesmo não é gate: é o réu assinando o próprio
# alvará. Esta é a lição mais cara do projeto INSS (ADR 0003 desta fábrica):
# lá, os gates de total se desligavam quando a partição não era a declarada,
# e o packet dizia ACEITO mesmo assim. 82 milhões de linhas publicadas sem
# que nada jamais as tivesse conferido.
#
# Formato de cada entrada:
#   "2026-01":
#     count_linhas: 41572553
#     sum_<coluna>: "78521752562.12"     # string: float perde centavo
#     min_<coluna>: "0.00"
#     max_<coluna>: "183725.76"
#     linhas_invalidas: 0
#     medido_em: "2026-09-16"
#     evidencia: "evidence/_totais-202601.json"
#
# Partição SEM entrada aqui publica ACEITO_SEM_ANCORA — visível no
# `make status` com marca ~?, nunca confundida com ACEITO.
controle_por_particao: {}

# ═════════════════════════════════════════════════════════════
# COLUNAS
# ═════════════════════════════════════════════════════════════
# NAO_MEDIDO. `make perfil` lê o cabeçalho real e PROPÕE esta lista;
# você confirma. O gerador não inventa nome de campo.
#
# Quando preencher, cada entrada é:
#   - pos: 0                 # posição, não nome — cabeçalho pode repetir
#     nome: minha_coluna     # o nome que a fábrica usa
#     origem: "Minha Coluna" # como a fonte escreveu
#     tipo: texto            # texto | inteiro | decimal | data
colunas: []

# ═════════════════════════════════════════════════════════════
# GRÃO — o que cada linha significa
# ═════════════════════════════════════════════════════════════
grao:
  silver: {{GRAO_SILVER}}
  gold: {{GRAO_GOLD}}

# ═════════════════════════════════════════════════════════════
# DINHEIRO — ADR 0002
# ═════════════════════════════════════════════════════════════
# Toda coluna aqui vira DECIMAL(18,2) no Silver e ganha gate anti-float
# no Gold. O gate existe porque `avg()` no DuckDB devolve DOUBLE: o defeito
# fica no TIPO, não no valor, e a soma continua batendo enquanto o centavo
# se perde na borda.
colunas_monetarias: {{COLUNAS_MONETARIAS}}

# ═════════════════════════════════════════════════════════════
# CHAVES SUSPEITAS — bijeção a provar
# ═════════════════════════════════════════════════════════════
# Um código só é chave enquanto for bijetivo com o que ele nomeia. Se a fonte
# reciclar um código, agregações passam a somar coisas diferentes — e o total
# continua batendo. Cada coluna aqui ganha gate no Silver que prova a bijeção.
#
# Lição DF-INSS-005: o inverso também engana. Um código que aparece sob muitos
# rótulos PARECE não-único, mas pode ser um segundo fato no mesmo campo.
# MEÇA os dois sentidos antes de compor chave — uma chave composta errada
# FRAGMENTA a entidade, e o total continua batendo do mesmo jeito.
chaves_suspeitas: {{CHAVES_SUSPEITAS}}

# ═════════════════════════════════════════════════════════════
# SENTINELAS — presentes e válidos, não são erro
# ═════════════════════════════════════════════════════════════
# Valor que ocupa a posição de um dado real sem ser um. NUNCA excluir,
# NUNCA imputar: vira categoria própria no Gold.
#
# ⚠ Raciocine por CLASSE, não por código. No INSS o contrato listava só o
#   998 ("INSS paga direto") e o 996 ("Acordos Internacionais") passou meses
#   ranqueado como se fosse banco. Se um código é sentinela, pergunte quais
#   OUTROS pertencem à mesma classe.
sentinelas: {{SENTINELAS}}

# ═════════════════════════════════════════════════════════════
# DEFEITOS DA FONTE — catálogo
# ═════════════════════════════════════════════════════════════
# Vazio até alguém medir. Um catálogo vazio significa "ninguém olhou ainda",
# NÃO "a fonte é limpa". Toda fonte real tem defeito; a fábrica classifica.
#
# Classificações: CONFIRMED_SOURCE_DEFECT · MODERN_DEFECT ·
#                 CONTRACT_AMBIGUITY · UNRESOLVED
#
# Formato:
#   - id: DF-{{SLUG_UPPER}}-001
#     campo: "nome_da_coluna"
#     descricao: "o que está errado"
#     impacto_medido: {linhas_afetadas: 0}
#     evidencia: "como foi comprovado"
#     classificacao: CONFIRMED_SOURCE_DEFECT
#     tratamento: "o que a fábrica faz — preservar, marcar, escalar"
defeitos_fonte: []

# ═════════════════════════════════════════════════════════════
# REGRAS DE ACEITAÇÃO — o que reprova
# ═════════════════════════════════════════════════════════════
aceitacao:
  bronze:
    - "toda linha tem o mesmo número de colunas que o contrato declara"
    - "rejeicoes == 0 — linha malformada reprova o lote inteiro"
    - "count e soma conferem com a âncora da partição   # tolerância ZERO"
    - "sem âncora: publica ACEITO_SEM_ANCORA, nunca ACEITO"
  silver:
    - "coluna monetária é DECIMAL(18,2), nunca float"
    - "count(silver) == count(bronze)                   # tolerância ZERO"
    - "sum(silver) == sum(bronze)                       # tolerância ZERO"
    - "count e soma conferem com a âncora               # tolerância ZERO"
    - "toda chave_suspeita continua bijetiva"
    - "data em ISO-8601, sem nulo silencioso"
  gold:
    - "grão único, sem duplicata"
    - "sum(gold) == sum(silver)                         # tolerância ZERO"
    - "sum(gold) == âncora da fonte                     # tolerância ZERO"
    - "toda coluna monetária é DECIMAL — avg() devolve DOUBLE (ADR 0002)"
    - "sentinela em linha própria, jamais agregada nem ranqueada"

# ═════════════════════════════════════════════════════════════
# TRATAMENTO DE REJEIÇÃO
# ═════════════════════════════════════════════════════════════
rejeicao:
  regra: "linha fora do layout declarado é rejeitada"
  ao_rejeitar:
    - "ZERO artefato — nenhum Parquet parcial é gravado"
    - "registrar em evidence/: posição, motivo, bytes crus"
    - "a execução inteira falha se rejeicoes > 0"
  proibido: "descartar linha em silêncio ou 'corrigir' o número de colunas"

# ═════════════════════════════════════════════════════════════
# RESTRIÇÕES
# ═════════════════════════════════════════════════════════════
restricoes:
  deduplicacao: {{DEDUP}}
  motivo_dedup: "{{MOTIVO_DEDUP}}"
  validade_dos_dominios: "medidos por partição. Revalidar a cada uma."
