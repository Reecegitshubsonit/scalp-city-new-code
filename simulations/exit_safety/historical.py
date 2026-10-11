"""Offline underlying-only execution-lag sensitivity, forward 60/30 split.
No option prices invented. Reuses existing signals and historical run function,
changing only exit detection/fill semantics in an isolated in-memory copy.
"""
import sys,json,statistics,collections,random
from pathlib import Path
sys.path.insert(0,str(Path('backtest').resolve()))
import filters as F
OUT=Path('simulations/exit_safety')
rows={}
for ticker in F.TICKERS:
 bars=F.load(ticker)
 for i,(_,o,h,l,c,v) in enumerate(bars):F.bars_hl[ticker,i]=(h,l,c)
 rows[ticker]=F.prepare(bars)
days=sorted({r['t'].date() for r in rows['SPY']})
train,test=set(days[:60]),set(days[60:])
base=Path('backtest/filters.py').read_text().split('def run(t, rows, cfg):',1)[1].split('\n\nbars_hl = {}',1)[0]
base='def experiment(t, rows, cfg):'+base
base=base.replace('hit_s = l <= stop if sig == "CALL" else h >= stop','hit_s = c <= stop if sig == "CALL" else c >= stop').replace('hit_t = h >= tgt if sig == "CALL" else l <= tgt','hit_t = c >= tgt if sig == "CALL" else c <= tgt')
# Latch first exit decision, then fill at later available close, capped at session flatten.
a='''                    if hit_s or hit_t or yend.time() >= FLAT or j == len(xs)-1:
                        why = 'STOP' if hit_s else 'TARGET' if hit_t else 'TIME'
                        for _ in range(LAG):
                            if j+1 >= len(xs) or xs[j]['t'].time() >= __import__('datetime').time(15,54): break
                            j += 1
                        y = xs[j]; c = y['c']; exit_end = y['t'] + timedelta(minutes=1)
                        R = ((c-ent) if sig == 'CALL' else (ent-c))/atr
                        break
'''
start=base.index('                    if hit_s:')
end=base.index('                    j += 1',start)
base=base[:start]+a+base[end:]
ns=dict(F.__dict__);exec(base,ns)
# Select on train data only using no extra execution lag.
ns['LAG']=0
rank=[]
for name,cfg in F.VARIANTS:
 tr=[x for t in F.TICKERS for x in ns['experiment'](t,rows[t],cfg) if x['day'] in train]
 rank.append((statistics.mean(x['R'] for x in tr),name,cfg))
_,chosen,cfg=max(rank,key=lambda x:x[0])
output={'scope':'Underlying ATR only; not option P&L or full production replay','train_days':60,'test_days':30,'selected_on_train':chosen,'results':[]}
for name,config in [('baseline',{}),(chosen,cfg)]:
 for lag in (0,1,2):
  ns['LAG']=lag
  tr=[x for t in F.TICKERS for x in ns['experiment'](t,rows[t],config) if x['day'] in test]
  byday=collections.defaultdict(list)
  for x in tr:byday[str(x['day'])].append(x['R'])
  rng=random.Random(20261009);ds=list(byday);samples=[]
  for _ in range(2000):
   blocks=[byday[rng.choice(ds)] for _ in ds]
   samples.append(sum(map(sum,blocks))/sum(map(len,blocks)))
  samples.sort();mean=statistics.mean(x['R'] for x in tr)
  output['results'].append({'variant':name,'extra_lag_minutes':lag,'trades':len(tr),'gross_atr':mean,'day_bootstrap_95_interval':[samples[50],samples[1949]],'cost_sensitivity':{str(cost):mean-cost for cost in (0,.1,.2,.3)}})
(OUT/'historical-results.json').write_text(json.dumps(output,indent=2))
print(json.dumps(output,indent=2))
