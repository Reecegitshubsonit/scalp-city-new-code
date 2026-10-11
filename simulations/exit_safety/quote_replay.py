"""Causal paper execution replay using captured bid/ask, quote time and displayed size.
Synthetic entry/exit schedule exercises integration; it is NOT a strategy backtest.
No network, no orders. A quoted price is a simulated opportunity, not a guaranteed fill.
"""
from pathlib import Path
from datetime import datetime,timedelta
from types import SimpleNamespace
import json,sys,tempfile,threading
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent/'candidate'))
from scalpcity.safe_engine import SafeEngine
from scalpcity.config import Settings
from scalpcity.events import EventLog
from scalpcity.types import Quote,Bar,ET
CONTRACT='QQQ261012P00751000'

class RecordedBroker:
    capability='PAPER'
    def __init__(self,clock,cache,depth,lag,fee):
        self.clock,self.cache,self.depth,self.lag,self.fee=clock,cache,depth,lag,fee
        self.orders={};self.lock=threading.RLock();self.cash=0.0;self.position=0;self.fills=[]
    def submit(self,o):
        with self.lock:
            self.orders[o['client_order_id']]={**o,'due':self.clock[0]+timedelta(seconds=self.lag),'filled_qty':0,'avg_price':None,'fees':0,'fill_time':None,'status':'SUBMITTED'}
            return self.poll(o['client_order_id'])
    def poll(self,oid):
        with self.lock:
            o=self.orders[oid];q=self.cache.get(o['contract']);now=self.clock[0]
            if o['status']=='SUBMITTED' and now>=o['due'] and q and 0<=(now-q.ts).total_seconds()<=2:
                buy=o['kind']=='BUY_OPEN';px=q.ask if buy else q.bid
                size=self.depth.get((o['contract'],'ask' if buy else 'bid'),0)
                if size>=o['qty'] and ((buy and px<=o['limit']) or (not buy and px>=o['limit'])):
                    n=o['qty'];fee=n*self.fee
                    self.depth[(o['contract'],'ask' if buy else 'bid')]-=n
                    o.update(status='FILLED',filled_qty=n,avg_price=px,fees=fee,fill_time=now.isoformat())
                    self.position+=n if buy else -n
                    self.cash+=(-px if buy else px)*n*100-fee
                    self.fills.append(dict(side='BUY' if buy else 'SELL',qty=n,price=px,fee=fee,at=now.isoformat(),quote_at=q.ts.isoformat()))
            return {k:o[k] for k in ('client_order_id','status','filled_qty','avg_price','fees','fill_time')}
    def cancel(self,oid):
        with self.lock:
            self.poll(oid)
            if self.orders[oid]['status']!='FILLED':self.orders[oid]['status']='CANCELLED'
            return self.poll(oid)


def replay(rows,lag,fee):
    clock=[datetime.fromisoformat(rows[0]['observed_at'])];cache={};depth={};broker=RecordedBroker(clock,cache,depth,lag,fee)
    with tempfile.TemporaryDirectory() as tmp:
        e=SafeEngine(Settings(daily_loss=10000,daily_goal=10000),EventLog(tmp,'quote-replay'),broker,SimpleNamespace(get=lambda c,t:cache.get(c)),Path(tmp)/'state.json',now_fn=lambda:clock[0])
        e.start_session(clock[0].date(),{})
        e.reconcile(dict(observed_at=clock[0].isoformat(),positions={},orders=[]))
        b=e.by_id['QQQ-VWAP'];attempted=False;entry_time=None;underlying=None;fresh=0;rejected=0
        def drain():
            for _ in range(2):
                for f,op in list(e.futures.values()):f.result(timeout=3)
                e.service()
        try:
            for row in rows:
                clock[0]=datetime.fromisoformat(row['observed_at'])
                if row.get('error_type'):continue
                for r in row['data']:
                    if row['kind']=='options' and r['symbol']==CONTRACT:
                        q=Quote(CONTRACT,datetime.fromtimestamp(r['quote_time']/1000,ET),float(r['bid']),float(r['ask']))
                        if r.get('delay_minutes',0) or not 0<=(clock[0]-q.ts).total_seconds()<=2:rejected+=1;continue
                        fresh+=1;cache[CONTRACT]=q
                        depth[(CONTRACT,'bid')]=int(r['bid_size']);depth[(CONTRACT,'ask')]=int(r['ask_size'])
                    elif row['kind']=='underlying' and r['symbol']=='QQQ':
                        stamp=datetime.fromtimestamp(r['quote_time']/1000,ET)
                        if 0<=(clock[0]-stamp).total_seconds()<=2:
                            # Explicit bid/ask midpoint observation, not stale last-trade price.
                            underlying=(float(r['bid'])+float(r['ask']))/2
                            if not attempted and CONTRACT in cache:
                                bar=Bar('QQQ',clock[0]-timedelta(minutes=1),underlying,underlying,underlying,underlying,1)
                                e.ind['QQQ'].atr.value=.03
                                intent=b._fire(bar,e.ind['QQQ'],'PUT')[0]
                                e._execute(b,intent,bar,e.ind['QQQ']);attempted=True;entry_time=clock[0]
                            if b.position and b.position.entry_price is not None:
                                if entry_time and (clock[0]-entry_time).total_seconds()>=45:b.exit_reason=b.exit_reason or 'SIMULATION_END'
                                e.monitor('QQQ',underlying,stamp)
                drain()
            drain()
            closed=b.position is None and b.trades==1
            if closed:assert abs(b.pnl_day-broker.cash)<.00001
            return dict(lag_seconds=lag,fee_per_contract_per_side=fee,fresh_quotes=fresh,rejected_quotes=rejected,
                        filled_orders=len(broker.fills),closed=closed,remaining_contracts=broker.position,
                        engine_net_pnl=b.pnl_day,independent_cash_flow=round(broker.cash,2),fills=broker.fills,
                        accounting_matches=closed and abs(b.pnl_day-broker.cash)<.00001)
        finally:e.close()


def main():
    path=ROOT/'data/exit-safety/market-capture.jsonl';rows=[json.loads(l) for l in path.read_text().splitlines()]
    results=[replay(rows,lag,fee) for lag in (0,.5,1,2) for fee in (.05,.65)]
    report=dict(purpose='Integration/accounting validation, not strategy profitability',feed='Webull sandbox snapshot quotes',first_observation=rows[0]['observed_at'],last_observation=rows[-1]['observed_at'],records=len(rows),capture_errors=sum('error_type' in x for x in rows),contract=CONTRACT,results=results,limitations=['90-second sample and one seeded contract, not a representative trading sample.','Entry is deliberately seeded; 0.03 underlying threshold and 45-second fallback are test inputs.','Polling can miss updates; displayed liquidity does not guarantee real fills or queue priority.','Fees are explicit sensitivity assumptions. No quote extrapolation or synthetic bid/ask from bars.'])
    (ROOT/'simulations/exit_safety/evidence/quote-replay.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({**report,'results':[{k:v for k,v in r.items() if k!='fills'} for r in results]},indent=2))
if __name__=='__main__':main()
