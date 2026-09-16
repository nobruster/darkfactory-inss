[project]
name = "darkfactory-{{SLUG}}"
version = "0.1.0"
description = "{{PERGUNTA}}"
requires-python = ">=3.12"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]

# O que NÃO se ignora em lugar nenhum: F821 (nome indefinido) e B (bugs).
# F821 já quebrou um validador inteiro no projeto INSS — uma string sem
# aspas vira nome indefinido e o script morre só quando aquele ramo roda.

[tool.ruff.lint.per-file-ignores]
# Lambda de conveniência para consulta DuckDB: `q = lambda s: ...`.
# Trocar por def aqui tornaria o código mais longo sem ficar mais claro.
"scripts/build_silver.py" = ["E731"]
"scripts/build_gold.py" = ["E731"]
"scripts/eval_doutrina.py" = ["E731"]
"scripts/ancorar_bronze.py" = ["E731"]

# Scripts de varredura: E701/E702 (statement na mesma linha) e SIM115
# (open sem context manager) são legítimos — o processo termina logo depois.
"scripts/perfil_cobertura.py" = ["E701", "E702", "SIM115"]
"scripts/totais_controle.py" = ["E701", "E702", "SIM115"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "-q --strict-markers"
markers = [
    "integracao: exige lakehouse construído (pule com -m 'not integracao')",
]
