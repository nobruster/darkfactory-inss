import collections
import io
import json
import time
import zipfile

BASE="/home/nobru/darkfactory-inss"
z=zipfile.ZipFile(f"{BASE}/_raw/fonte.zip"); n=z.namelist()[0]
ufs=collections.Counter(); bancos=collections.Counter(); esp=collections.Counter()
tot=0; t0=time.time()
with z.open(n) as f:
    t=io.TextIOWrapper(f,encoding="latin-1")
    t.readline()
    for line in t:
        p=line.split(";")
        if len(p)>=14:
            ufs[p[4].strip()]+=1
            bancos[p[6].strip()]+=1
            esp[p[12].strip()]+=1
            tot+=1
            if tot % 5_000_000 == 0:
                print(f"{tot:,} linhas | {time.time()-t0:.0f}s | UFs={len(ufs)}", flush=True)
out={"total_linhas":tot,"ufs":dict(ufs),"bancos":dict(bancos),"especies":dict(esp),"segundos":round(time.time()-t0)}
json.dump(out, open(f"{BASE}/evidence/_perfil-cobertura.json","w"), ensure_ascii=False, indent=2)
print(f"CONCLUIDO {tot:,} linhas | {len(ufs)} UFs | {len(esp)} especies | {time.time()-t0:.0f}s", flush=True)
