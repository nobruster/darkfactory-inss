"""Totais de controle da fonte. Sao a ancora de integridade — o 173.45 desta fabrica."""
import zipfile, io, json, time
from decimal import Decimal
BASE="/home/nobru/darkfactory-inss"
z=zipfile.ZipFile(f"{BASE}/_raw/fonte.zip"); n=z.namelist()[0]
tot=0; soma=Decimal("0"); ruins=0; t0=time.time()
minv=None; maxv=None
with z.open(n) as f:
    t=io.TextIOWrapper(f,encoding="latin-1"); t.readline()
    for line in t:
        p=line.rstrip("\r\n").split(";")
        if len(p)<14: ruins+=1; continue
        tot+=1
        v=p[9].strip().replace(".","").replace(",",".")
        try:
            d=Decimal(v); soma+=d
            if minv is None or d<minv: minv=d
            if maxv is None or d>maxv: maxv=d
        except Exception: ruins+=1
        if tot % 10_000_000 == 0: print(f"{tot:,} | {time.time()-t0:.0f}s", flush=True)
out={"count_linhas":tot,"linhas_invalidas":ruins,
     "sum_vl_liquido":str(soma),"min_vl_liquido":str(minv),"max_vl_liquido":str(maxv),
     "segundos":round(time.time()-t0)}
json.dump(out, open(f"{BASE}/evidence/_totais-controle.json","w"), indent=2)
print(json.dumps(out, indent=2), flush=True)
