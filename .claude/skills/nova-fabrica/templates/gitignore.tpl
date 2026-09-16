# Artefatos de runtime — produzidos rodando a fábrica, nunca clonando.
# Um clone novo precisa executar o pipeline para populá-los.

_raw/*.zip
_raw/*.csv
_raw/*.parquet
landing/
lakehouse/
.venv/

# perfilamentos e logs são descartáveis — regeráveis a qualquer momento
evidence/*.log
evidence/_*.json
evidence/_*.txt

# ⚠ EXCEÇÃO: os totais de controle NÃO são descartáveis. O contrato os cita
# como evidência da âncora de cada partição, e um contrato que aponta para
# arquivo fora do git não prova nada — a cadeia de custódia terminaria no
# primeiro clone.
!evidence/_totais-*.json
!evidence/_perfil-*.json

# os packets de gate FICAM versionados: são a prova do que rodou, e quando.
# O padrão é <camada>-<particao>.json — partição nova entra sozinha.

__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
