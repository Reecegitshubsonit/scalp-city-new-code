"""Bounded read-only market capture for replay; no order endpoints."""
import os,sys,json,time
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scalpcity.webull_client import WebullClient
from scalpcity.types import ET
from scalpcity.guard import assert_paper_only,SANDBOX_HOST
for line in (ROOT/'.env').read_text().splitlines():
 if line.strip() and not line.startswith('#') and '=' in line:
  k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('\"\''))
OUT=ROOT/'data/exit-safety/market-capture.jsonl'
c=WebullClient.from_env(os.environ);assert_paper_only(os.environ,SANDBOX_HOST,c.accounts())
start=time.monotonic();n=0
with OUT.open('w') as f:
 while time.monotonic()-start<90:
  for kind,fn,args in [
   ('options',c.data.option_market_data.get_option_snapshot,('QQQ261012P00749000,SPY261012P00776000,QQQ261012P00751000','US_OPTION')),
   ('underlying',c.data.market_data.get_snapshot,('QQQ,SPY','US_STOCK'))]:
   try:
    resp=c._call(fn,*args);data=resp.json() if hasattr(resp,'json') else resp
    row={'kind':kind,'observed_at':datetime.now(ET).isoformat(),'data':data}
   except Exception as e:row={'kind':kind,'observed_at':datetime.now(ET).isoformat(),'error_type':type(e).__name__}
   f.write(json.dumps(row)+'\n');f.flush();n+=1
  time.sleep(.5)
print(json.dumps({'observations':n,'duration_s':round(time.monotonic()-start,2),'path':str(OUT)}))
