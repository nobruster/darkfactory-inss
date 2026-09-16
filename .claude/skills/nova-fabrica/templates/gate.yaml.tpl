# Cerca de escrita — {{DISPLAY_NAME}}
#
# Task-Specs estreitam autoridade. Esta política é o TETO PERMANENTE,
# que nenhuma tarefa pode alargar. A autoridade só desce, nunca sobe.
#
# Gerada por nova-fabrica em {{DATA}}.
version: 2

protected_paths:
  # ── genéricos ────────────────────────────────────────────────
  - "**/.git/**"
  - "**/.cvg/**"
  - "**/.env"
  - "**/.env.*"
  - "**/secrets/**"
  - "**/credentials/**"
  - "**/*_key*"
  - "**/*_secret*"
  - "**/id_rsa*"
  - ".cvg/gate.yaml"            # protege a si mesmo
  - ".github/workflows/**"      # senão o CI seria desligado para "passar"

  # ── desta fábrica ────────────────────────────────────────────
  - "_raw/**"                   # a fonte: chmod 444 + sha256
  - "contracts/**"              # O JUIZ — ver docs/adrs/
  - "docs/adrs/**"              # decisões vinculantes
  - "evidence/**"               # packets de gate: prova do que rodou

max_changed_files: 12

# ─────────────────────────────────────────────────────────────
# POR QUE cada bloco existe
# ─────────────────────────────────────────────────────────────
# _raw/       Reescrever a fonte apagaria a evidência do defeito. A cadeia de
#             custódia (sha256 nos packets) deixaria de provar nada.
#             O .sha256 congela JUNTO com o .zip: registro de custódia
#             gravável ao lado de fonte 444 não protege coisa alguma.
#
# contracts/  Ajustar a expectativa para um teste passar é trapaça, não
#             conserto. Quando o resultado diverge, classifica-se.
#
# docs/adrs/  Um ADR aceito é vinculante. Mudar de ideia se faz com ADR novo
#             que supersede o anterior — nunca editando o antigo. Editar
#             apaga o registro de que a decisão anterior existiu.
#
# evidence/   O packet registra o que aconteceu. Editá-lo falsifica o
#             histórico. Packet errado se REEXECUTA; conferência retroativa
#             vira arquivo NOVO, ao lado do antigo.
#
# ⚠ O padrão aqui tem de CASAR com arquivo real. No INSS este bloco dizia
#   "evidence/*-run.json" e casava com zero arquivo: a cerca existia no
#   papel. `make cercas` confere que este arquivo e o .claude/settings.json
#   continuam de acordo.
#
# max_changed_files: não é sobre permissão, é sobre tamanho revisável. Uma
# tarefa que toca 200 arquivos produziu algo que ninguém consegue avaliar.
