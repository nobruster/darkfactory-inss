"""Testa o contrato contra os dados reais. O contrato erra? A fonte erra? Dizemos qual."""
import zipfile, io, yaml, json, collections, sys
BASE="/home/nobru/darkfactory-inss"
c=yaml.safe_load(open(f"{BASE}/contracts/layout.yaml"))
esp_oficial=json.load(open(f"{BASE}/contracts/_especies.json"))

# domínios declarados no contrato
declarados={col["nome"]:set(col["dominio"]) for col in c["colunas"]
            if isinstance(col.get("dominio"), list)}
pos={col["nome"]:col["pos"] for col in c["colunas"]}

obs=collections.defaultdict(collections.Counter)
esp_vistos=collections.Counter()
ncols=collections.Counter(); tot=0

z=zipfile.ZipFile(f"{BASE}/_raw/fonte.zip"); n=z.namelist()[0]
with z.open(n) as f:
    t=io.TextIOWrapper(f,encoding="latin-1"); t.readline()
    for line in t:
        p=line.rstrip("\r\n").split(";")
        ncols[len(p)]+=1
        if len(p)>=14:
            tot+=1
            for campo in declarados: obs[campo][p[pos[campo]].strip()]+=1
            esp_vistos[p[12].strip().zfill(2)]+=1

print(f"linhas: {tot:,}")
print(f"contagem de colunas: {dict(ncols)}")
print()
falhas=0
for campo, dom in declarados.items():
    vistos=set(obs[campo])
    extras=vistos-dom; faltam=dom-vistos
    status="OK" if not extras else "VIOLADO"
    if extras: falhas+=1
    print(f"[{status:8}] {campo}")
    if extras: print(f"           nos dados mas NAO no contrato: {sorted(extras)}")
    if faltam: print(f"           no contrato mas nao nos dados: {sorted(faltam)}")

orfas=set(esp_vistos)-set(esp_oficial)
print()
print(f"[{VIOLADO if orfas else OK:8}] especie_codigo x dicionario oficial")
print(f"           codigos nos dados: {len(esp_vistos)} | no dicionario: {len(esp_oficial)}")
if orfas: print(f"           ORFAOS (sem descricao oficial): {sorted(orfas)}"); falhas+=1
print()
print(f"RESULTADO: {falhas} violacao(oes)")
