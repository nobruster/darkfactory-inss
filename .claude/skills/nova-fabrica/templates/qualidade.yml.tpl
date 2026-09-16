name: qualidade

# Roda sem dados: não há fonte nem lakehouse no CI.
# O que se prova aqui é o que NÃO depende de execução — lint, testes
# unitários, integridade do contrato e conformidade das cercas.
#
# As evals de integração rodam localmente, contra o lakehouse real.
#
# Gerado por nova-fabrica em {{DATA}} para {{DISPLAY_NAME}}.

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  codigo:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: instalar
        run: |
          python -m pip install -q --upgrade pip
          pip install -q ruff pytest pyyaml duckdb "pyarrow>=25,<26"

      - name: lint
        run: ruff check ingestion scripts tests

      - name: testes unitários
        run: pytest tests/ -q -m "not integracao"

  contrato:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -q pyyaml

      - name: contrato é YAML válido e coerente
        run: |
          python - <<'PY'
          import pathlib
          import sys

          import yaml

          c = yaml.safe_load(
              pathlib.Path("contracts/layout.yaml").read_text(encoding="utf-8"))
          erros = []

          # Um contrato NAO_MEDIDO é estado legítimo — a fábrica recusa
          # construir e o CI passa. O que NÃO pode é dizer medido: true
          # com os campos vazios: isso é juiz de mentira.
          if c.get("medido"):
              if not c.get("colunas"):
                  erros.append("medido: true mas colunas: []")
              if not c.get("controle_por_particao"):
                  erros.append("medido: true mas controle_por_particao: {}")
              declaradas = (c.get("fonte") or {}).get("colunas")
              if declaradas and len(c["colunas"]) != declaradas:
                  erros.append(
                      f"declara {declaradas} colunas, define {len(c['colunas'])}")
              pos = sorted(col["pos"] for col in c["colunas"])
              if pos != list(range(len(pos))):
                  erros.append(f"posições não são contíguas: {pos}")

          # Toda âncora precisa dos dois números, como string.
          for part, a in (c.get("controle_por_particao") or {}).items():
              if "count_linhas" not in a:
                  erros.append(f"{part}: âncora sem count_linhas")
              if not a.get("evidencia"):
                  erros.append(f"{part}: âncora sem arquivo de evidência")

          # Todo defeito catalogado precisa de classificação.
          for d in c.get("defeitos_fonte") or []:
              if "classificacao" not in d:
                  erros.append(f"{d.get('id', '?')} sem classificacao")

          if erros:
              print("CONTRATO INVÁLIDO")
              for e in erros:
                  print(f"  - {e}")
              sys.exit(1)

          estado = "MEDIDO" if c.get("medido") else "NAO_MEDIDO"
          print(f"contrato v{c['version']} OK · {estado} · "
                f"{len(c.get('defeitos_fonte') or [])} defeitos catalogados")
          PY

      - name: artefatos congelados íntegros
        run: |
          if [ -s contracts/CHECKSUMS.txt ]; then
            cd contracts && sha256sum -c CHECKSUMS.txt
          else
            echo "CHECKSUMS.txt vazio — nenhuma fonte congelada ainda"
          fi

  cercas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -q pyyaml

      - name: as duas cercas concordam entre si
        run: python scripts/verificar_cercas.py

  congelado:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: ADR aceito não se edita — supersede-se
        run: |
          if [ "${{ github.event_name }}" != "pull_request" ]; then
            echo "não é PR — pulando"; exit 0
          fi
          BASE="${{ github.event.pull_request.base.sha }}"
          # M=modificado, D=apagado, R=renomeado. A=adicionado é permitido:
          # ADR novo é exatamente como se muda de ideia.
          TOCADO=$(git diff --name-only --diff-filter=MDR "$BASE" HEAD -- docs/adrs/)
          if [ -n "$TOCADO" ]; then
            echo "BLOQUEIO: ADR existente alterado ou removido:"
            echo "$TOCADO" | sed 's/^/  /'
            echo ""
            echo "Um ADR aceito é vinculante. Mudar de ideia se faz com um ADR"
            echo "NOVO que supersede o anterior — nunca editando o antigo."
            exit 1
          fi
          echo "docs/adrs/: nenhum ADR existente foi tocado"

      - name: pasta congelada só muda com ADR que a nomeia
        run: |
          if [ "${{ github.event_name }}" != "pull_request" ]; then
            echo "não é PR — pulando"; exit 0
          fi
          BASE="${{ github.event.pull_request.base.sha }}"
          MUDOU=$(git diff --name-only "$BASE" HEAD -- contracts/ _raw/)
          if [ -z "$MUDOU" ]; then
            echo "nada mudou em pasta congelada"; exit 0
          fi
          echo "pasta congelada alterada:"
          echo "$MUDOU" | sed 's/^/  /'
          ADR_NOVO=$(git diff --name-only --diff-filter=A "$BASE" HEAD -- docs/adrs/)
          if [ -z "$ADR_NOVO" ]; then
            echo ""
            echo "BLOQUEIO: mudança em pasta congelada sem ADR novo."
            echo "Ajustar o juiz para um teste passar é trapaça, não conserto."
            exit 1
          fi
          # Não basta existir um ADR novo: ele tem de NOMEAR o arquivo que
          # mudou. Senão, um ADR sobre qualquer assunto destrava qualquer
          # edição do contrato.
          FALTOU=""
          for arq in $MUDOU; do
            if ! grep -qF "$(basename "$arq")" $ADR_NOVO; then
              FALTOU="$FALTOU $arq"
            fi
          done
          if [ -n "$FALTOU" ]; then
            echo ""
            echo "BLOQUEIO: há ADR novo, mas nenhum menciona:"
            for a in $FALTOU; do echo "  $a"; done
            exit 1
          fi
          echo "ADR que justifica:"
          echo "$ADR_NOVO" | sed 's/^/  /'
