"""Read-only comparison of recorded broker fills and local event-log fills."""
import sys,json,collections,hashlib
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent/'candidate'))
from scalpcity.order_records import normalize_order,normalize_positions
OUT=ROOT/'simulations/exit_safety/evidence';PRIVATE=ROOT/'data/exit-safety'
cap=json.loads((OUT/'capture-status.json').read_text())
cutoff=datetime.fromisoformat(cap['captured_at'])
raw=(ROOT/'logs/2026-10-09-live.jsonl').read_bytes()
E=[json.loads(l) for l in raw.splitlines() if datetime.fromisoformat(json.loads(l)['time'])<=cutoff]
(PRIVATE/'events-snapshot.json').write_text(json.dumps(E))
orders=[];unsupported=0
for r in json.loads((PRIVATE/'order_history.json').read_text()):
 try:orders.append(normalize_order(r))
 except ValueError:unsupported+=1
fills=[e for e in E if e['kind']=='fill'];used=set();matched=[];unmatched=[];ambiguous=[]
for e in fills:
 candidates=[]
 for o in orders:
  if o['client_order_id'] in used or not o['filled_qty']:continue
  delay=(datetime.fromisoformat(o['fill_time'].replace('Z','+00:00'))-datetime.fromisoformat(e['time'])).total_seconds()
  if o['contract']==e['contract'] and o['side']==('BUY' if e['reason_code']=='ENTRY_FILL' else 'SELL') and o['filled_qty']==e['qty'] and abs(o['avg_price']-e['fill_price'])<.0001 and -5<=delay<=180:
   candidates.append((abs(delay),delay,o))
 if len(candidates)==1:
  _,delay,o=candidates[0];used.add(o['client_order_id']);matched.append((e,o,delay))
 elif candidates:ambiguous.append(e['seq'])
 else:unmatched.append(e['seq'])
positions,other=normalize_positions(json.loads((PRIVATE/'positions.json').read_text()))
local=collections.Counter()
for e in fills:local[e['contract']]+=e['qty']*(1 if e['reason_code']=='ENTRY_FILL' else -1)
diff=[{'contract':s,'logged_qty':local.get(s,0),'broker_qty':positions.get(s,0)} for s in sorted(set(local)|set(positions)) if local.get(s,0)!=positions.get(s,0)]
# Closed trade cash flows, broker fees where uniquely matched; never silently impute unmatched fees.
byseq={e['seq']:o for e,o,d in matched};open_trades={};closed=[]
for e in E:
 b=e['bot']
 if e['kind']=='fill' and e['reason_code']=='ENTRY_FILL':open_trades[b]=[e]
 elif e['kind']=='fill' and e['reason_code']=='EXIT_FILL' and b in open_trades:open_trades[b].append(e)
 elif e['kind']=='trade_closed' and b in open_trades:
  legs=open_trades.pop(b)
  if len(legs)==2 and all(x['seq'] in byseq for x in legs):
   a,z=legs;fees=sum(byseq[x['seq']]['fees'] for x in legs)
   gross=(z['fill_price']-a['fill_price'])*a['qty']*100
   assert abs(gross-e['pnl'])<.01
   closed.append({'bot':b,'entry_seq':a['seq'],'exit_seq':z['seq'],'gross':round(gross,2),'fees':round(fees,2),'net':round(gross-fees,2)})
res=dict(cutoff=cutoff.isoformat(),log_sha256=hashlib.sha256(raw).hexdigest(),log_fills=len(fills),matched_fills=len(matched),unmatched_sequences=unmatched,ambiguous_sequences=ambiguous,broker_option_orders=len(orders),unsupported_orders=unsupported,position_mismatches=diff,other_account_instruments=other,matched_closed_trades=len(closed),matched_closed_gross=round(sum(x['gross'] for x in closed),2),matched_closed_fees=round(sum(x['fees'] for x in closed),2),matched_closed_net=round(sum(x['net'] for x in closed),2),matched_closed_details=closed,unmatched_broker_filled_orders=sum(o['filled_qty']>0 and o['client_order_id'] not in used for o in orders),limitations=['Matching uses contract, side, quantity, price and a 180-second window; old logs lack order IDs.','Snapshot positions may change during read-only capture; reconcile again before any activation.','Broker sandbox fills verify accounting, not realistic market execution.'])
(OUT/'broker-reconciliation.json').write_text(json.dumps(res,indent=2))
print(json.dumps({k:v for k,v in res.items() if k!='matched_closed_details'},indent=2))
