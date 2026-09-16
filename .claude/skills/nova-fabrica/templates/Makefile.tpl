# Usa o venv quando existe; cai no python3 do sistema quando não. Sem isso,
# o primeiro `make` de um clone novo morre com "No such file or directory"
# em vez de dizer o que realmente falta.
PY   := $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3)
PART ?= {{PARTICAO_EXEMPLO}}

# Toda etapa é um script Python. O Makefile só encadeia — nada de curl, sed
# ou lógica aqui dentro: o que decide fica versionado e testável.
#
# Fábrica gerada por nova-fabrica em {{DATA}}.
# Fonte: {{DISPLAY_NAME}}
# Pergunta: {{PERGUNTA}}

ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: help init fetch check refetch perfil contrato bronze silver gold all \
        status ancora cercas conferir lint test evals agentes qa clean

help: ## lista os alvos
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'
	@echo ""
	@echo "  partição: PART=$(PART)   (ex: make all PART=...)"
	@$(PY) scripts/estado_contrato.py --breve 2>/dev/null || true

init: ## cria o venv e instala as dependências
	@python3 -m venv .venv
	@$(PY) -m pip install -q --upgrade pip
	@$(PY) -m pip install -q duckdb "pyarrow>=25,<26" pyyaml ruff pytest requests
	@echo "ambiente pronto"

# ── medição: o caminho obrigatório antes de construir ────────

fetch: ## baixa a fonte e congela (não rebaixa o que já existe)
	@$(PY) ingestion/fetch_fonte.py --particao $(PART)

check: ## pergunta ao servidor se a fonte mudou, sem baixar
	@$(PY) ingestion/fetch_fonte.py --particao $(PART) --check-remoto

refetch: ## rebaixa deliberadamente (reprocessamento)
	@$(PY) ingestion/fetch_fonte.py --particao $(PART) --force

perfil: ## varre a fonte e mede: layout, domínios, cobertura
	@$(PY) scripts/perfil_cobertura.py --particao $(PART)

ancora: ## mede a ÂNCORA desta partição direto da fonte
	@$(PY) scripts/totais_controle.py --particao $(PART)
	@echo ""
	@echo "  registre em controle_por_particao: com  make contrato"

contrato: ## transfere o que foi medido para o contrato (pede confirmação)
	@$(PY) scripts/promover_medicao.py --particao $(PART)

# ── construção: recusa enquanto o contrato não estiver medido ─

bronze: ## fonte -> landing Parquet (gates: rejeições, count, soma)
	@$(PY) scripts/estado_contrato.py --exigir-medido
	@$(PY) ingestion/ingest_bronze.py --particao $(PART)

silver: ## bronze -> grão conformado (gates de total e de chave)
	@$(PY) scripts/estado_contrato.py --exigir-medido
	@$(PY) scripts/build_silver.py --particao $(PART)

gold: ## silver -> a resposta da pergunta (gates de total e sentinela)
	@$(PY) scripts/estado_contrato.py --exigir-medido
	@$(PY) scripts/build_gold.py --particao $(PART)

all: fetch perfil ancora contrato bronze silver gold ## a linha completa
	@echo ""
	@echo "  prove o resultado: make evals PART=$(PART)"

status: ## estado dos packets de todas as partições
	@$(PY) scripts/status.py

conferir: ## confere um Bronze já publicado contra a âncora (auditoria)
	@$(PY) scripts/ancorar_bronze.py --particao $(PART)

# ── qualidade ────────────────────────────────────────────────

lint: ## ruff sobre ingestion, scripts e tests
	@$(PY) -m ruff check ingestion scripts tests

test: ## testes unitários (não precisam de lakehouse)
	@$(PY) -m pytest tests/ -q -m "not integracao"

cercas: ## as duas cercas de escrita concordam entre si?
	@$(PY) scripts/verificar_cercas.py

agentes: ## gate dos agentes em .claude/agents/
	@bash .claude/skills/novo-agente/quality-gate.sh --strict

evals: ## as evals de integração (exigem lakehouse construído)
	@bash scripts/rodar_evals.sh $(PART)

qa: lint test cercas agentes ## tudo que não precisa de dados — o que o CI roda
	@echo ""
	@echo "  qa OK — para provar os dados: make evals PART=$(PART)"

clean: ## DESTRUTIVO: apaga landing e lakehouse desta partição (a fonte fica)
	@test "$(CONFIRM)" = "clean-runtime" || { echo "rerun com CONFIRM=clean-runtime"; exit 2; }
	@rm -rf landing/$(PART) lakehouse/$(PART)
	@echo "runtime de $(PART) apagado — fonte e contratos permanecem"
