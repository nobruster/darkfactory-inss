PY   := .venv/bin/python
COMP ?= 2026-01

# Toda etapa é um script Python. O Makefile só encadeia — nada de curl, sed
# ou lógica aqui dentro: o que decide fica versionado e testável.

ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: help init fetch check bronze silver gold all status ranking perfil contrato clean \
        lint test evals agentes qa ancora cercas conferir skills fabrica

help: ## lista os alvos
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'
	@echo ""
	@echo "  competência: COMP=$(COMP)   (ex: make all COMP=2026-02)"

init: ## cria o venv e instala as dependências
	@python3 -m venv .venv
	@$(PY) -m pip install -q --upgrade pip
	@$(PY) -m pip install -q duckdb "pyarrow>=25,<26" pyyaml openpyxl ruff pytest
	@echo "ambiente pronto"

fetch: ## baixa a fonte e congela (não rebaixa o que já existe)
	@$(PY) ingestion/fetch_fonte.py --competencia $(COMP)

check: ## pergunta ao servidor se a fonte mudou, sem baixar
	@$(PY) ingestion/fetch_fonte.py --competencia $(COMP) --check-remoto

refetch: ## rebaixa deliberadamente (reprocessamento)
	@$(PY) ingestion/fetch_fonte.py --competencia $(COMP) --force

perfil: ## perfila a fonte (cobertura + totais de controle)
	@$(PY) scripts/perfil_cobertura.py --competencia $(COMP)
	@$(PY) scripts/totais_controle.py --competencia $(COMP)

ancora: ## mede a âncora desta competência direto da fonte (~50s)
	@$(PY) scripts/totais_controle.py --competencia $(COMP)
	@echo ""
	@echo "  registre o resultado em controle_por_competencia: do contrato"
	@echo "  (exige ADR — o contrato é congelado)"

cercas: ## as duas cercas de escrita concordam entre si?
	@$(PY) scripts/verificar_cercas.py

conferir: ## confere um Bronze já publicado contra a âncora (auditoria)
	@$(PY) scripts/ancorar_bronze.py --competencia $(COMP)

contrato: ## valida domínios e dicionário contra os dados reais
	@$(PY) scripts/extrair_dicionario.py --check
	@$(PY) scripts/validar_contrato.py --competencia $(COMP)

bronze: ## fonte -> landing Parquet (gates: rejeições, count, soma)
	@$(PY) ingestion/ingest_bronze.py --competencia $(COMP)

silver: ## bronze -> grão conformado (gates: count, soma, espécie)
	@$(PY) scripts/build_silver.py --competencia $(COMP)

gold: ## silver -> concentração bancária por UF (7 gates)
	@$(PY) scripts/build_gold.py --competencia $(COMP)

all: fetch contrato bronze silver gold ## a linha completa, do download ao Gold
	@echo ""
	@echo "  prove o resultado: make evals COMP=$(COMP)"

status: ## estado dos packets de todas as competências
	@$(PY) scripts/status.py

ranking: ## top 10 bancos por valor pago
	@$(PY) scripts/ranking.py --competencia $(COMP)

# ── qualidade ────────────────────────────────────────────────

lint: ## ruff sobre ingestion, scripts e tests
	@$(PY) -m ruff check ingestion scripts tests

test: ## testes unitários (não precisam de lakehouse)
	@$(PY) -m pytest tests/ -q -m "not integracao"

evals: ## as 3 evals de integração (exigem lakehouse construído)
	@bash scripts/rodar_evals.sh $(COMP)

agentes: ## gate dos agentes em .claude/agents/
	@bash .claude/skills/novo-agente/quality-gate.sh --strict

skills: ## gate das skills (novo-agente e nova-fabrica)
	@bash .claude/skills/novo-agente/quality-gate.sh --strict
	@bash .claude/skills/nova-fabrica/quality-gate.sh --strict

fabrica: ## gera uma fábrica nova a partir do menu (SLUG=nome)
	@test -n "$(SLUG)" || { echo "uso: make fabrica SLUG=<slug-do-menu>"; exit 2; }
	@bash .claude/skills/nova-fabrica/scaffold.sh $(SLUG)

qa: lint test skills cercas ## tudo que não precisa de dados — o mesmo que o CI roda
	@echo ""
	@echo "  qa OK — para provar os dados: make evals COMP=$(COMP)"

clean: ## DESTRUTIVO: apaga landing e lakehouse desta competência (a fonte fica)
	@test "$(CONFIRM)" = "clean-runtime" || { echo "rerun com CONFIRM=clean-runtime"; exit 2; }
	@rm -rf landing/$(COMP) lakehouse/$(COMP) evidence/*-$(subst -,,$(COMP)).json
	@echo "runtime de $(COMP) apagado — fonte e contratos permanecem"
