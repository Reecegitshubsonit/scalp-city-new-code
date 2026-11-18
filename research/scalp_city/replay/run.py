"""Offline observed-snapshot stateful replay. No option-PnL claims or network."""
from pathlib import Path
import sys,json,csv,hashlib,re
from collections import defaultdict,Counter
from dataclasses import replace
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2]
sys.path.insert(0,str(REPO))
from scalpcity.bot import Bot
from scalpcity.config import Settings,BOT_SPECS
from scalpcity.indicators import IndicatorSet
from scalpcity.triggers import VwapCross,Ema50Cross,RangeBreak
from scalpcity.types import Bar,Fill
from coordination import DirectionBook
OUT=ROOT/'results'
TRIGGERS={'vwap':VwapCross,'ema50':Ema50Cross,'range':RangeBreak}
EXCLUDED={('SPY-VWAP','09:43'),('QQQ-EMA50','09:55'),('QQQ-RANGE','09:55')}


def snapshot(x):
    ind=IndicatorSet()
    for name in ('ema9','ema21','ema50'):
        getattr(ind,name).value=x[name];getattr(ind,name).n=100
    ind.atr.value=x['atr'];ind.vwap.value=x['vwap'];ind.last_close=x['price']
    return ind


def bar_for(ticker,stamp,x):
    # Only close/time used. No claims about synthetic O/H/L or volume.
    p=x['price'];return Bar(ticker,stamp-timedelta(minutes=1),p,p,p,p,0)


class ReplayBot(Bot):
    def __init__(self,*args,context,**kwargs):
        super().__init__(*args,**kwargs);self.ctx=context;self.token=None

    def _fire(self,bar,ind,side):
        c=self.ctx; clock=bar.end.strftime('%H:%M');reason=None
        if (self.bot_id,clock) in c.get('excluded',EXCLUDED):reason='EXCLUDED_RESTART_ENTRY'
        elif c['squeeze'] and ind.squeezed(self.s.squeeze_atr):reason='ALL_BOT_SQUEEZE'
        elif c['floor'] and ind.atr.value/bar.close*10000<3:reason='ATR_FLOOR'
        elif c['vwap']:
            window=[v for t,v in c['history'][self.ticker] if bar.end-timedelta(minutes=30)<=t<=bar.end]
            if len(window)>=25:
                share=sum(v['price']>v['vwap'] for v in window)/len(window)
                if (side=='PUT' and share>=.8) or (side=='CALL' and share<=.2):reason='VWAP_PERSISTENCE'
        if reason:c['vetoes'][reason]+=1;return []
        token=f'{self.bot_id}:{bar.end.isoformat()}'
        if c['coordinate'] and not c['book'].reserve(token,self.ticker,side,self.s.contracts):
            c['vetoes']['OPPOSING_POSITION']+=1;return []
        self.token=token
        return super()._fire(bar,ind,side)

    def _manage(self,bar,now,ind):
        if not self.ctx['latched']:self.exit_reason=None
        return super()._manage(bar,now,ind)


def load():
    ev=[json.loads(s) for s in (REPO/'logs/2026-10-09-live.jsonl').read_text().splitlines()]
    by={};conflicts=0
    for e in ev:
        if e['kind']=='tick' and e['inputs'].get('price') is not None:
            key=(e['time'],e['ticker']);x=e['inputs'];fields={k:x[k] for k in ('price','vwap','ema9','ema21','ema50','atr')}
            if key in by and fields!=by[key]:conflicts+=1
            by[key]=fields
    assert conflicts==0
    observations=[(datetime.fromisoformat(t),tk,x) for (t,tk),x in sorted(by.items())]
    expanded=list(csv.DictReader((ROOT.parent/'data/expanded/trades_expanded.csv').open()))
    retries={(r['bot'],t,r['side']) for r in expanded for t in r['exit_retry_times'].split(';') if t}
    range_line=(REPO/'reports/dissect-2026-10-09/signal_table.md').read_text().splitlines()[0]
    ranges={tk:(float(lo),float(hi)) for tk,lo,hi in re.findall(r'(IWM|QQQ|SPY) ([\d.]+)-([\d.]+)',range_line)}
    assert len(ranges)==3
    return observations,expanded,retries,ranges


def simulate(observations,retries,ranges,*,name,trend=False,latched=True,coordinate=False,squeeze=False,vwap=False,floor=False,delay=0,reverse=False,range_shift=0):
    ctx=dict(latched=latched,coordinate=coordinate,squeeze=squeeze,vwap=vwap,floor=floor,
             book=DirectionBook(),history=defaultdict(list),vetoes=Counter())
    settings=Settings(trend_side=trend)
    bots=[ReplayBot(tk,spec,TRIGGERS[key](settings.charge_range_atr),settings,context=ctx) for tk in ('QQQ','SPY','IWM') for key,spec in BOT_SPECS.items()]
    if reverse:bots.reverse()
    active={};closed=[];attempts=[];due={};max_positions=0;overlap_steps=0
    for now,tk,x in observations:
        ctx['history'][tk].append((now,x));ind=snapshot(x);bar=bar_for(tk,now,x)
        for bot in [b for b in bots if b.ticker==tk]:
            if bot.spec.trigger=='range':
                if now.strftime('%H:%M')<'09:45':
                    bot.trigger.prev_close=bar.close
                    continue
                bot.trigger.lo=ranges[tk][0]+range_shift;bot.trigger.hi=ranges[tk][1]+range_shift
            out=bot.on_bar(bar,ind)
            for intent in out.intents:
                if intent.kind=='BUY_OPEN':
                    active[bot.bot_id]=dict(bot=bot.bot_id,ticker=tk,side=intent.right,entry_time=now.isoformat(),entry_price=bar.close,atr=ind.atr.value,token=bot.token)
                    if coordinate:ctx['book'].update_entry(bot.token,intent.qty,'FILLED')
                    # Constant unit price solely exercises Bot's fill/cooldown state transitions.
                    # No computed option PnL is reported; all monetary risk gates are out of scope.
                    bot.on_fill(Fill(bot.bot_id,'BUY_OPEN','RESEARCH_UNIT',intent.qty,1,'state_only',now),ind.as_dict())
                else:
                    prior=active[bot.bot_id]
                    due.setdefault(bot.bot_id,now+timedelta(minutes=delay))
                    failure=(bot.bot_id,now.strftime('%H:%M'),prior['side']) in retries
                    waiting=now<due[bot.bot_id]
                    attempts.append(dict(bot=bot.bot_id,time=now.isoformat(),reason=intent.reason,failed=failure,delay_wait=waiting))
                    if failure or waiting:
                        bot.on_order_failed('SELL_CLOSE','SCENARIO_NO_FILL' if failure else 'SCENARIO_DELAY');continue
                    sg=1 if prior['side']=='CALL' else -1
                    move=sg*(bar.close-prior['entry_price'])/prior['atr']
                    closed.append(dict(**prior,exit_time=now.isoformat(),exit_price=bar.close,exit_reason=intent.reason,underlying_atr=move))
                    if coordinate:ctx['book'].reduce(prior['token'],intent.qty)
                    bot.on_fill(Fill(bot.bot_id,'SELL_CLOSE','RESEARCH_UNIT',intent.qty,1,'state_only',now),ind.as_dict())
                    active.pop(bot.bot_id);due.pop(bot.bot_id,None)
            if coordinate:assert ctx['book'].invariant()
        max_positions=max(max_positions,len(active))
        if any(len({r['side'] for r in active.values() if r['ticker']==ticker})>1 for ticker in ('QQQ','SPY','IWM')):overlap_steps+=1
    vals=[r['underlying_atr'] for r in closed]
    summary=dict(name=name,trend=trend,latched=latched,coordinate=coordinate,squeeze=squeeze,vwap=vwap,floor=floor,
                 delay=delay,reverse=reverse,range_shift=range_shift,trades=len(vals),open=len(active),
                 total_atr=sum(vals),mean_atr=sum(vals)/len(vals) if vals else None,
                 positive_pct=sum(v>0 for v in vals)/len(vals)*100 if vals else None,
                 worst_atr=min(vals) if vals else None,max_positions=max_positions,opposing_observation_steps=overlap_steps,
                 failure_injections=sum(a['failed'] for a in attempts),
                 position_minutes=sum((datetime.fromisoformat(r['exit_time'])-datetime.fromisoformat(r['entry_time'])).total_seconds()/60 for r in closed),
                 mean_after_0_1_atr_burden=(sum(vals)/len(vals)-.1) if vals else None,
                 mean_after_0_2_atr_burden=(sum(vals)/len(vals)-.2) if vals else None,
                 vetoes=dict(ctx['vetoes']))
    return dict(summary=summary,trades=closed,open_positions=list(active.values()),exit_attempts=attempts)


def retry_traces(expanded,observations):
    results=[]
    for row in expanded:
        if not int(row['exit_retries']):continue
        path=[(t,tk,x) for t,tk,x in observations if tk==row['ticker'] and row['signal_time']<=t.strftime('%H:%M')<=row['exit_fill_time']]
        for latched in (False,True):
            ctx=dict(latched=latched)
            key=row['trigger'].lower();b=ReplayBot(row['ticker'],BOT_SPECS[key],TRIGGERS[key](1),Settings(trend_side=False),context=ctx)
            t,tk,x=path[0];ind=snapshot(x);bar=bar_for(tk,t,x)
            # Replay actual entry; entry filters/coordination deliberately absent in this isolated exit experiment.
            Bot._fire(b,bar,ind,row['side'])
            b.on_fill(Fill(b.bot_id,'BUY_OPEN',row['option_symbol'],10,float(row['entry_fill_price']),'recorded',t),ind.as_dict())
            traces=[]
            failed_times=set(row['exit_retry_times'].split(';'))
            for t,tk,x in path[1:]:
                ind=snapshot(x);bar=bar_for(tk,t,x)
                intents=b._manage(bar,t,ind)
                if not intents:continue
                fail=t.strftime('%H:%M') in failed_times
                traces.append(dict(time=t.strftime('%H:%M'),reason=intents[0].reason,injected_failure=fail,underlying=x['price']))
                b.on_order_failed('SELL_CLOSE','INJECTED_NO_FILL')
                if not fail:break # hypothetical success at next observed close; no option quote assumed
            results.append(dict(n=int(row['n']),mode='current_latched' if latched else 'legacy_re_evaluate',
                                logged_exit_time=row['exit_fill_time'],logged_pnl=float(row['pnl_logged']),attempts=traces))
    return results


def main():
    OUT.mkdir(exist_ok=True)
    before={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((REPO/'scalpcity').glob('*.py'))}
    observations,expanded,retries,ranges=load()
    baseline=dict(trades=len(expanded),logged_pnl=sum(float(r['pnl_logged']) for r in expanded))
    traces=retry_traces(expanded,observations)
    variants=[]
    for trend in (False,True):
        prefix='ema' if trend else 'cross'
        variants.extend([dict(name=prefix+'_legacy',trend=trend,latched=False),dict(name=prefix+'_latched',trend=trend)])
        for label,flags in [('unchanged',{}),('squeeze',dict(squeeze=True)),('vwap',dict(vwap=True)),('squeeze_vwap',dict(squeeze=True,vwap=True)),('atr3',dict(floor=True))]:
            base=dict(name=prefix+'_coordinated_'+label,trend=trend,coordinate=True,**flags)
            variants.append(base)
            for delay in (1,2):variants.append(dict(base,name=base['name']+f'_delay{delay}',delay=delay))
            variants.append(dict(base,name=base['name']+'_reverse_priority',reverse=True))
            for shift in (-.01,.01):variants.append(dict(base,name=base['name']+f'_range_shift{shift}',range_shift=shift))
    runs=[simulate(observations,retries,ranges,**v) for v in variants]
    for run in runs:
        if run['summary']['coordinate']:assert run['summary']['opposing_observation_steps']==0
        assert run['summary']['open']==0
    output=dict(factual_baseline=baseline,observation_count=len(observations),ranges=ranges,
                isolated_retry_traces=traces,runs=runs)
    (OUT/'replay.json').write_text(json.dumps(output,indent=2)+'\n')
    with (OUT/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(runs[0]['summary']));w.writeheader();w.writerows(r['summary'] for r in runs)
    trade_rows=[dict(variant=r['summary']['name'],**t) for r in runs for t in r['trades']]
    with (OUT/'trades.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(trade_rows[0]));w.writeheader();w.writerows(trade_rows)
    by_bot=[]
    for run in runs:
        for bot in sorted({r['bot'] for r in run['trades']}):
            values=[r['underlying_atr'] for r in run['trades'] if r['bot']==bot]
            by_bot.append(dict(variant=run['summary']['name'],bot=bot,trades=len(values),total_atr=sum(values),mean_atr=sum(values)/len(values)))
    with (OUT/'by_bot.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(by_bot[0]));w.writeheader();w.writerows(by_bot)
    after={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((REPO/'scalpcity').glob('*.py'))}
    assert before==after
    inputs=[REPO/'logs/2026-10-09-live.jsonl',ROOT.parent/'data/expanded/trades_expanded.csv',REPO/'reports/dissect-2026-10-09/signal_table.md',ROOT/'plan.json',ROOT/'stress_followup.json',Path(__file__),ROOT/'coordination.py',ROOT/'report.py',ROOT/'test_replay.py']
    (OUT/'manifest.json').write_text(json.dumps(dict(inputs={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},production_unchanged=True,production_hashes=before),indent=2)+'\n')
    for r in runs:
        s=r['summary']
        if not s['delay'] and not s['reverse'] and not s['range_shift']:
            print(f"{s['name']:34} n={s['trades']:3} mean={s['mean_atr']:+.3f} total={s['total_atr']:+.2f} positive={s['positive_pct']:.1f}% failures={s['failure_injections']}")
    print('trials',len(runs),'observations',len(observations),'retry scenarios',len(traces))

if __name__=='__main__':main()
