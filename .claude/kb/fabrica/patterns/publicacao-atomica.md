# Publicação atômica

Nenhuma camada desta fábrica publica parcialmente. Ou passa em todos os gates e
publica inteiro, ou não deixa rastro.

## O padrão

```python
parcial = BASE / "landing" / f".{comp}.parcial"
destino = BASE / "landing" / comp

shutil.rmtree(parcial, ignore_errors=True)
parcial.mkdir(parents=True)

# ... escreve tudo em parcial ...

if falhas:
    shutil.rmtree(parcial, ignore_errors=True)   # ZERO artefato
    return 1

parcial.rename(destino)    # só agora o destino existe
```

O `rename` é atômico no sistema de arquivos. Não há instante em que `destino`
exista pela metade.

## Por que não gravar direto

Um arquivo que existe **parece válido**. Se o Bronze gravasse 30 milhões de
linhas e falhasse na 31ª, alguém leria aquilo achando que era a competência
inteira — e o total estaria errado sem nada acusar.

A ausência é inequívoca. A presença parcial engana.

## Onde está implementado

| Script | Parcial | Destino |
|---|---|---|
| `ingestion/fetch_fonte.py` | `.fonte-AAAAMM.parcial` | `fonte-AAAAMM.zip` |
| `ingestion/ingest_bronze.py` | `.AAAA-MM.parcial/` | `landing/AAAA-MM/` |
| `scripts/build_silver.py` | `.AAAA-MM.parcial/` | `lakehouse/AAAA-MM/` |

O Gold é exceção: ele cria tabela dentro do DuckDB já existente, então o padrão é
`drop table if exists` + recriar, e `drop` de novo se um gate reprovar.

## O que acompanha a publicação

Não basta o dado. O landing publica três arquivos:

```
NW_..._B202607230000001.parquet          o dado
NW_..._B202607230000001.parquet.sha256   prova de integridade
parquet-manifest.json                     "terminei de escrever, pode ler"
```

O manifesto é o sinal de prontidão. Sem ele, um leitor poderia pegar o Parquet
no meio da gravação — o mesmo problema que o `.parcial` resolve, uma camada
acima.

## A cadeia de custódia

O manifesto amarra origem e produto:

```json
{
  "fonte_sha256":   "428626857daf...",
  "parquet_sha256": "cd1e2b2ad9b9..."
}
```

Qualquer um verifica que **este** Parquet veio **daquela** fonte. Se a fonte
mudar, o sha muda, e o vínculo quebra visivelmente.

## Anti-pattern

```python
# NÃO — deixa estado intermediário visível
destino.mkdir(exist_ok=True)
for bloco in dados:
    escreve(destino / f"parte-{i}.parquet")
if falhas:
    return 1          # e os arquivos já escritos ficam lá
```

## Como testar

Interrompa no meio (`Ctrl+C` durante o Bronze) e confira:

```bash
ls landing/          # não deve existir o diretório da competência
ls landing/.*parcial # o parcial pode ter sobrado — é inofensivo, será limpo
```

Ver: `contracts/layout.yaml` seção `rejeicao` · ADR 0002
