"""Bounded candidate runner. Defaults to no-order shadow mode.
Paper mode is disabled unless release checks pass; never invokes legacy run_live.py.
"""
import argparse,json,os,queue,threading,time
from pathlib import Path
from datetime import datetime
from scalpcity.safe_engine import SafeEngine
from scalpcity.shadow_adapter import ShadowAdapter
from scalpcity.paper_adapter import PaperAdapter
from scalpcity.webull_client import WebullClient
from scalpcity.config import Settings,TICKERS
from scalpcity.contracts import occ_symbol,next_trading_day,atm_strike
from scalpcity.events import EventLog
from scalpcity.live import LiveFeed,market_open
from scalpcity.types import ET,Quote
from scalpcity.guard import assert_paper_only,SANDBOX_HOST

class QuoteCache:
    def __init__(self):self.rows={};self.lock=threading.RLock()
    def put(self,q):
        with self.lock:self.rows[q.symbol]=q
    def get(self,c,t):
        with self.lock:return self.rows.get(c)

def run(client,engine,feed,cache,duration,tape):
    """Worker queues decouple market/network requests from risk and control processing."""
    updates=queue.Queue(maxsize=1000);stop=threading.Event();subscriptions=set();sub_lock=threading.Lock();last_quote={}
    def publish(item):
        try:updates.put_nowait(item)
        except queue.Full:stop.set()  # don't trade after silently dropping an unbounded backlog
    def bars():
        while not stop.is_set():
            try:
                if market_open(datetime.now(ET)):
                    for b in feed.poll():publish(('bar',b))
            except Exception as ex:publish(('error',type(ex).__name__))
            stop.wait(5)
    def snapshots():
        while not stop.is_set():
            try:
                if not market_open(datetime.now(ET)):stop.wait(1);continue
                r=client._call(client.data.market_data.get_snapshot,','.join(TICKERS),'US_STOCK')
                rows=r.json() if hasattr(r,'json') else r
                publish(('underlying',rows))
                with sub_lock:symbols=','.join(sorted(subscriptions))
                if symbols:
                    r=client._call(client.data.option_market_data.get_option_snapshot,symbols,'US_OPTION')
                    publish(('options',r.json() if hasattr(r,'json') else r))
            except Exception as ex:publish(('error',type(ex).__name__))
            stop.wait(.5)
    threads=[threading.Thread(target=fn,daemon=True) for fn in (bars,snapshots)]
    for thread in threads:thread.start()
    started=time.monotonic();counts={'bar':0,'underlying':0,'options':0,'error':0}
    try:
        with Path(tape).open('a') as out:
            while time.monotonic()-started<duration and not stop.is_set():
                try:kind,data=updates.get(timeout=.2)
                except queue.Empty:kind,data=None,None
                now=datetime.now(ET)
                if kind:
                    counts[kind]+=1
                    out.write(json.dumps({'observed_at':now.isoformat(),'kind':kind,'data':data},default=str)+'\n');out.flush()
                if kind=='bar':
                    # Do not enter from historical backlog; catch-up belongs to startup.
                    if 0<=(now-data.end).total_seconds()<=10:engine.on_bar(data)
                elif kind=='options':
                    for r in data:
                        if r.get('delay_minutes',0):continue
                        try:q=Quote(r['symbol'],datetime.fromtimestamp(r['quote_time']/1000,ET),float(r['bid']),float(r['ask']))
                        except (KeyError,ValueError,TypeError):continue
                        cache.put(q)
                        with engine.lock:
                            for b in engine.bots:
                                if b.position and b.position.contract==q.symbol:last_quote[b.bot_id]=q.ts
                elif kind=='underlying':
                    for r in data:
                        try:
                            ticker=r['symbol'];stamp=datetime.fromtimestamp(r['quote_time']/1000,ET)
                            price=(float(r['bid'])+float(r['ask']))/2
                        except (KeyError,ValueError,TypeError):continue
                        with sub_lock:
                            for right in ('CALL','PUT'):
                                subscriptions.add(occ_symbol(ticker,next_trading_day(now.date()),right,atm_strike(price)))
                        engine.monitor(ticker,price,stamp)
                engine.service()
                engine.check_stale(now,feed.last_bar_wall,last_quote)
                with engine.lock,sub_lock:
                    subscriptions.update(b.position.contract for b in engine.bots if b.position and b.position.contract)
            return counts
    finally:
        stop.set()
        for thread in threads:thread.join(timeout=2)
        engine.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['shadow','paper'],default='shadow')
    ap.add_argument('--seconds',type=int,default=30);ap.add_argument('--output',required=True)
    args=ap.parse_args()
    if not 1<=args.seconds<=3600:ap.error('seconds must be 1..3600')
    if args.mode=='paper':
        from preflight import evaluate
        if not evaluate()['ready_for_paper_order_activation']:raise SystemExit('BLOCKED: release checks not passed; no broker orders sent')
    root=Path(__file__).resolve().parents[3]
    for line in (root/'.env').read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('\"\''))
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    # Shadow sessions are deliberately fresh. Reusing journal state requires a persistent broker fixture.
    if args.mode=='shadow' and (output/'state.json').exists():raise SystemExit('use a fresh output directory for each shadow run')
    client=WebullClient.from_env(os.environ)
    accounts=client.accounts();assert_paper_only(os.environ,SANDBOX_HOST,accounts)
    cache=QuoteCache();adapter=ShadowAdapter(cache) if args.mode=='shadow' else PaperAdapter(client,os.environ,accounts,SANDBOX_HOST)
    engine=SafeEngine(Settings(),EventLog(str(output),args.mode),adapter,cache,output/'state.json')
    feed=LiveFeed(client,TICKERS,lambda:datetime.now(ET))
    try:
        now=datetime.now(ET);prior,today=feed.startup(now.date())
        engine.start_session(now.date(),prior);engine.catch_up(today)
        if args.mode=='paper' and engine.state_path.exists():engine.load_state()
        if not engine.reconcile(adapter.snapshot(list(engine.orders))):raise SystemExit('BLOCKED: account reconciliation failed')
        result=run(client,engine,feed,cache,args.seconds,output/'market.jsonl')
        (output/'summary.json').write_text(json.dumps({'mode':args.mode,'remote_order_calls':0 if args.mode=='shadow' else 'adapter','counts':result},indent=2))
        print(json.dumps({'mode':args.mode,'counts':result,'output':str(output)}))
    except BaseException:
        if not engine.stopping:engine.close()
        raise
if __name__=='__main__':main()
