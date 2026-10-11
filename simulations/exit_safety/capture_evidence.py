"""Read-only sandbox evidence capture. Never calls place/cancel, never prints credentials."""
import sys,json,os
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scalpcity.webull_client import WebullClient
from scalpcity.guard import assert_paper_only,SANDBOX_HOST
from scalpcity.types import ET
OUT=ROOT/'simulations/exit_safety/evidence'
PRIVATE=ROOT/'data/exit-safety';PRIVATE.mkdir(parents=True,exist_ok=True)
for line in (ROOT/'.env').read_text().splitlines():
 if line.strip() and not line.startswith('#') and '=' in line:
  k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('\"\''))
def clean(o):
 if isinstance(o,dict):return {k:clean(v) for k,v in o.items() if not any(x in k.lower() for x in ('account_id','secret','token','app_key'))}
 if isinstance(o,list):return [clean(v) for v in o]
 return o
result={'captured_at':datetime.now(ET).isoformat(),'mode':'read-only sandbox'}
try:
 c=WebullClient.from_env(os.environ)
 acct=assert_paper_only(os.environ,SANDBOX_HOST,c.accounts())
 aid=acct['account_id']
 r=c._call(c.trade.account_v2.get_account_position,aid)
 positions=r.json() if hasattr(r,'json') else r
 (PRIVATE/'positions.json').write_text(json.dumps(clean(positions),indent=2))
 result['positions_received']=True
 pages=[];last=None
 for i in range(20):
  r=c._call(c.trade.order_v2.get_order_history,aid,page_size=100,last_client_order_id=last)
  page=r.json() if hasattr(r,'json') else r
  if not isinstance(page,list):
   result['history_shape']=type(page).__name__;break
  pages.extend(page)
  if len(page)<100:result['history_complete']=True;break
  nxt=page[-1].get('client_order_id')
  if not nxt or nxt==last:result['history_complete']=False;break
  last=nxt
 (PRIVATE/'order_history.json').write_text(json.dumps(clean(pages),indent=2))
 result['history_orders']=len(pages)
 e=[json.loads(x) for x in (ROOT/'logs/2026-10-09-live.jsonl').read_text().splitlines()]
 contracts=sorted({x['contract'] for x in e if x['kind']=='fill'})[-3:]
 quotes=[]
 for contract in contracts:
  q=c.option_quote(contract)
  if q:
   quote,delay=q
   quotes.append({'symbol':contract,'market_at':quote.ts.isoformat(),'observed_at':datetime.now(ET).isoformat(),'bid':quote.bid,'ask':quote.ask,'delay_minutes':delay})
 (PRIVATE/'quote_samples.json').write_text(json.dumps(quotes,indent=2))
 result['quote_samples']=len(quotes)
except Exception as e:
 result['error_type']=type(e).__name__
 # No exception message: SDK/network errors can embed authentication headers.
(OUT/'capture-status.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
