PY   := .venv/bin/python
COMP ?= 2026-01

# Toda etapa é um script Python. O Makefile só encadeia — nada de curl, sed
# ou lógica aqui dentro: o que decide fica versionado e testável.

.PHONY: help init fetch check bronze silver gold all status ranking perfil contrato clean

help: ## lista os alvos
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'
	@echo ""
	@echo "  competência: COMP=$(COMP)   (ex: make all COMP=2026-02)"

init: ## cria o venv e instala as dependências
	@python3 -m venv .venv
	@$(PY) -m pip install -q --upgrade pip
	@$(PY) -m pip install -q duckdb pyarrow pyyaml openpyxl
	@echo "ambiente pronto"

fetch: ## baixa a fonte e congela (não rebaixa o que já existe)
	@$(PY) ingestion/fetch_fonte.py --competencia $(COMP)

check: ## pergunta ao servidor se a fonte mudou, sem baixar
	@$(PY) ingestion/fetch_fonte.py --competencia $(COMP) --check-remoto

refetch: ## rebaixa deliberadamente (reprocessamento)
	@$(PY) ingestion/fetch_fonte.py --competencia $(COMP) --force

perfil: ## perfila a fonte (cobertura + totais de controle)
	@$(PY) scripts/perfil_cobertura.py
	@$(PY) scripts/totais_controle.py

contrato: ## valida o contrato contra os dados reais
	@$(PY) scripts/validar_contrato.py

bronze: ## fonte -> landing Parquet (gates: rejeições, count, soma)
	@$(PY) ingestion/ingest_bronze.py --competencia $(COMP)

silver: ## bronze -> grão conformado (gates: count, soma, espécie)
	@$(PY) scripts/build_silver.py --competencia $(COMP)

gold: ## silver -> concentração bancária por UF (7 gates)
	@$(PY) scripts/build_gold.py --competencia $(COMP)

all: fetch bronze silver gold ## a linha completa, do download ao Gold

status: ## estado dos packets de todas as competências
	@$(PY) scripts/status.py

ranking: ## top 10 bancos por valor pago
	@$(PY) scripts/ranking.py --competencia $(COMP)

clean: ## DESTRUTIVO: apaga landing e lakehouse desta competência (a fonte fica)
	@test "$(CONFIRM)" = "clean-runtime" || { echo "rerun com CONFIRM=clean-runtime"; exit 2; }
	@rm -rf landing/$(COMP) lakehouse/$(COMP) evidence/*-$(subst -,,$(COMP)).json
	@echo "runtime de $(COMP) apagado — fonte e contratos permanecem"
