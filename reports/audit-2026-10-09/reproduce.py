import csv,json,collections,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path('backtest').resolve()))
import filters as F
rows={}
for t in F.TICKERS:
 bars=F.load(t)
 for i,(_,o,h,l,c,v) in enumerate(bars): F.bars_hl[t,i]=(h,l,c)
 rows[t]=F.prepare(bars)
ns=dict(F.__dict__)
source=Path('backtest/filters.py').read_text().split('def run(t, rows, cfg):',1)[1].split('\n\nbars_hl = {}',1)[0]
source='def run_close(t, rows, cfg):'+source
source=source.replace('hit_s = l <= stop if sig == "CALL" else h >= stop','hit_s = c <= stop if sig == "CALL" else c >= stop').replace('hit_t = h >= tgt if sig == "CALL" else l <= tgt','hit_t = c >= tgt if sig == "CALL" else c <= tgt')
source=source.replace('"STOP", -sa, yend','"STOP", ((c-ent) if sig == "CALL" else (ent-c))/atr, yend').replace('"TARGET", ta, yend','"TARGET", ((c-ent) if sig == "CALL" else (ent-c))/atr, yend')
exec(source,ns)
for name,cfg in [('baseline',{}),('filtered',dict(buffer=.2,trend=True,chop_all=True))]:
 for mode,fn in [('intrabar exact',F.run),('bar-close',ns['run_close'])]:
  tr=[x for t in F.TICKERS for x in fn(t,rows[t],cfg)]
  ds=collections.defaultdict(float)
  for x in tr:ds[x['day']]+=x['R']
  print(name,mode,'N',len(tr),'avgATR',round(statistics.mean(x['R'] for x in tr),4),'daily mean',round(statistics.mean(ds.values()),4))
E=[json.loads(l) for l in open('logs/2026-10-09-live.jsonl')]
cur={};closed=[]
for e in E:
 b=e['bot']; k=e['kind']; code=e['reason_code']
 if k=='order_sent' and code=='BUY_OPEN':cur[b]={'entry_order':e}
 if k=='fill' and code=='ENTRY_FILL':cur.setdefault(b,{})['entry']=e
 if k=='fill' and code=='EXIT_FILL':cur.setdefault(b,{})['exit']=e
 if k=='trade_closed':
  c=cur.pop(b);c['closed']=e;closed.append(c)
print('snapshot',E[-1]['time'],'closed',len(closed),'P&L',sum(c['closed']['pnl'] for c in closed))
import re
BA=re.compile(r'bid/ask ([\d.]+)/([\d.]+)')
# Use all order quotes, retaining last exit attempt.
orders={}
for e in E:
 if e['kind']=='order_sent':orders[(e['bot'],e['reason_code'],e['time'])]=e
qp=0
for c in closed:
 a,b=c['entry'],c['exit']; ea=orders[(a['bot'],'BUY_OPEN',a['time'])]; eb=orders[(b['bot'],'SELL_CLOSE',b['time'])]
 ba=BA.search(ea['reason_text']);bb=BA.search(eb['reason_text'])
 qp+=(float(bb[1])-float(ba[2]))*a['qty']*100
print('all-quote ask/bid scenario',round(qp))
print('last closed',closed[-1]['closed']['bot'],closed[-1]['closed']['time'],closed[-1]['closed']['pnl'])
print('open',[(b,c['entry']['contract']) for b,c in cur.items() if 'entry' in c])
