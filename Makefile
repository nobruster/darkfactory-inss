PY := .venv/bin/python
COMP := 2026-01
URL := https://armazenamento-dadosabertos.s3.sa-east-1.amazonaws.com/PDA_2025_2027/Grupos_de_dados/Benef%C3%ADcios+emitidos/D.SDA.PDA.003.EMI.202601.CSV.ZIP

.PHONY: help init fetch perfil bronze silver gold all status clean

help: ## lista os alvos
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'

init: ## cria o venv e instala as dependências
	@python3 -m venv .venv
	@$(PY) -m pip install -q --upgrade pip
	@$(PY) -m pip install -q duckdb pyarrow pyyaml openpyxl
	@echo "ambiente pronto"

fetch: ## baixa a fonte e congela (chmod 444 + sha256)
	@mkdir -p _raw
	@test -f _raw/fonte.zip || curl -sL -o _raw/fonte.zip "$(URL)"
	@cd _raw && sha256sum fonte.zip > fonte.zip.sha256
	@chmod 444 _raw/fonte.zip
	@echo "fonte congelada:"; cat _raw/fonte.zip.sha256

verify: ## confere que a fonte não mudou
	@cd _raw && sha256sum -c fonte.zip.sha256

perfil: ## perfila a fonte (cobertura + totais de controle)
	@$(PY) scripts/perfil_cobertura.py
	@$(PY) scripts/totais_controle.py

contrato: ## valida o contrato contra os dados reais
	@$(PY) scripts/validar_contrato.py

bronze: ## fonte -> landing Parquet (gates: rejeições, count, soma)
	@$(PY) ingestion/ingest_bronze.py

silver: ## bronze -> grão conformado (gates: count, soma, espécie)
	@$(PY) scripts/build_silver.py

gold: ## silver -> concentração bancária por UF (7 gates)
	@$(PY) scripts/build_gold.py

all: bronze silver gold ## a linha completa

status: ## mostra o estado dos packets de evidência
	@for f in bronze silver gold; do \
	  printf "  %-8s " $$f; \
	  test -f evidence/$$f-run.json \
	    && $(PY) -c "import json,sys;d=json.load(open('evidence/$$f-run.json'));print(d['status'], d.get('linhas',''))" \
	    || echo "(não executado)"; \
	done

ranking: ## top 10 bancos por valor pago
	@$(PY) -c "import duckdb; c=duckdb.connect('lakehouse/$(COMP)/inss.duckdb', read_only=True); \
	[print(f'  {i:>2}  {r[0]}  {r[1]:22} R\$$ {r[2]:>18,.2f}  {r[3]:>5}%') \
	 for i,r in enumerate(c.execute(\"select banco_codigo, max(banco_nome), sum(vl_total), round(100.0*sum(vl_total)/(select sum(vl_total) from gold_concentracao_bancaria),2) from gold_concentracao_bancaria where not e_inss_direto group by 1 order by 3 desc limit 10\").fetchall(),1)]"

clean: ## DESTRUTIVO: apaga landing e lakehouse (a fonte fica)
	@test "$(CONFIRM)" = "clean-runtime" || { echo "rerun com CONFIRM=clean-runtime"; exit 2; }
	@rm -rf landing lakehouse evidence/*-run.json
	@echo "runtime apagado — a fonte e os contratos permanecem"
