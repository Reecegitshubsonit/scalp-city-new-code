"""Offline signal-direction audit. No broker/client imports or connectivity."""
import csv
import json
import sys
from pathlib import Path
from datetime import datetime,timedelta
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]))
from scalpcity.config import Settings
from scalpcity.engine import Engine,build_bots
from scalpcity.indicators import IndicatorSet
from scalpcity.triggers import TriggerView
from scalpcity.types import Bar,Quote,ET

class MemoryLog:
    def append(self,*args,**kwargs):pass

class StubQuotes:
    def get(self,contract,when):return Quote(contract,when,1.00,1.01)

class CaptureBroker:
    def __init__(self):self.orders=[]
    def execute(self,intent,contract,quote,when):
        self.orders.append((intent,contract))
        return None  # deliberately no fill; no external broker


def snapshot(r):
    ind=IndicatorSet()
    for name in ('ema9','ema21','ema50'):
        getattr(ind,name).value=float(r[name+'_at_signal']);getattr(ind,name).n=100
    ind.vwap.value=float(r['vwap_at_signal'])
    ind.atr.value=float(r['atr_at_signal'])
    ind.last_close=float(r['signal_und_close'])
    return ind


def main():
    rows=list(csv.DictReader((ROOT/'data/expanded/trades_expanded.csv').open()))
    log=[json.loads(line) for line in (ROOT.parents[1]/'logs/2026-10-09-live.jsonl').read_text().splitlines()]
    results=[]
    for r in rows:
        ind=snapshot(r)
        bot=next(b for b in build_bots(Settings()) if b.bot_id==r['bot'])
        expected='CALL' if ind.ema9.value>ind.ema21.value else 'PUT'
        assert ind.ema9.value!=ind.ema21.value
        selected=bot._side(r['side'],ind)
        assert selected==expected
        raw_bot=next(b for b in build_bots(Settings(trend_side=False)) if b.bot_id==r['bot'])
        assert raw_bot._side(r['side'],ind)==r['side']
        entry=None
        if r['trigger'] in ('VWAP','EMA50'):
            prior=[e for e in log if e['seq']<int(r['signal_seq']) and e['bot']==r['bot'] and e['kind']=='tick'][-1]
            field='vwap' if r['trigger']=='VWAP' else 'ema50'
            bot.trigger.prev_close=prior['inputs']['price'];bot.trigger.prev_level=prior['inputs'][field]
            when=datetime.fromisoformat('2026-10-09T'+r['signal_time']+':00').replace(tzinfo=ET)
            p=ind.last_close
            bar=Bar(r['ticker'],when-timedelta(minutes=1),p,p,p,p,1000)
            out=bot.on_bar(bar,ind)
            assert len(out.intents)==1,(r['n'],bot.reason_code)
            entry=out.intents[0].right
            assert entry==expected
        results.append(dict(n=int(r['n']),bot=r['bot'],friday_side=r['side'],ema9=ind.ema9.value,
                            ema21=ind.ema21.value,current_selected_side=selected,
                            actual_trigger_checked=entry is not None,changed=selected!=r['side']))
    # Adversarial cross/EMA disagreement: every bot, both sides, trend on and off.
    matrix=[]
    for enabled in (True,False):
        for expected_trend in ('CALL','PUT'):
            settings=Settings(trend_side=enabled)
            engine=Engine(settings,MemoryLog(),CaptureBroker(),StubQuotes())
            for bot in engine.bots:
                cross='PUT' if expected_trend=='CALL' else 'CALL'
                ind=IndicatorSet();ind.atr.value=1;ind.last_close=100;ind.vwap.value=100
                ind.ema9.value=102 if expected_trend=='CALL' else 98
                ind.ema21.value=100;ind.ema50.value=100;ind.ema50.n=100
                when=datetime(2026,10,9,10,0,tzinfo=ET)
                bar=Bar(bot.ticker,when-timedelta(minutes=1),100,100,100,100,1000)
                out=bot._evaluate_flat(bar,when,ind,TriggerView(signal=cross,charge_pct=100))
                expected=expected_trend if enabled else cross
                assert len(out)==1 and out[0].right==expected
                position=bot.position
                assert (position.stop_und<100<position.target_und) if expected=='CALL' else (position.target_und<100<position.stop_und)
                engine._execute(bot,out[0],bar,ind)
                sent,contract=engine.broker.orders[-1]
                assert sent.right==expected and contract[len(bot.ticker)+6]==('C' if expected=='CALL' else 'P')
                matrix.append(dict(bot=bot.bot_id,trend_side=enabled,ema_side=expected_trend,cross=cross,order_side=sent.right,contract=contract))
    report=dict(snapshot_checks=len(results),real_cross_trigger_checks=sum(r['actual_trigger_checked'] for r in results),
                changed_vs_friday=sum(r['changed'] for r in results),order_route_cases=len(matrix),
                scope='Snapshot and routing audit, not stateful session replay or counterfactual profitability',
                rows=results,matrix=matrix)
    (ROOT/'results/direction_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','matrix')},indent=2))

if __name__=='__main__':main()
