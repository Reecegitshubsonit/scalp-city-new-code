"""60 complete historical sessions. Disconnected, no credentials or broker APIs."""
from pathlib import Path
import sys,json,csv,hashlib,bisect,random,statistics
from collections import defaultdict,Counter
from datetime import datetime,time,timedelta
from dataclasses import replace
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2];OUT=ROOT/'results'
sys.path.insert(0,str(REPO));sys.path.insert(0,str(ROOT.parent/'replay'))
from run import ReplayBot,TRIGGERS,snapshot
from coordination import DirectionBook
from scalpcity.config import Settings,BOT_SPECS,TICKERS
from scalpcity.indicators import IndicatorSet
from scalpcity.types import Bar,Fill,ET,Quote
from scalpcity.contracts import next_trading_day,atm_strike,occ_symbol
from scalpcity.risk import RiskGate

SOURCES=set()


def read_json(p):
    SOURCES.add(p);return json.loads(p.read_text())


def parse(rows,tk):
    bars={}
    for r in rows:
        t=datetime.fromisoformat(r['t'].replace('Z','+00:00')).astimezone(ET)
        if not time(9,30)<=t.time()<time(16):continue
        b=Bar(tk,t,float(r['o']),float(r['h']),float(r['l']),float(r['c']),float(r['v']))
        if t in bars and bars[t]!=b:raise ValueError('conflicting duplicate underlying bar')
        assert b.low<=min(b.open,b.close)<=max(b.open,b.close)<=b.high and b.volume>=0
        bars[t]=b
    return sorted(bars.values(),key=lambda b:b.ts)


def prepare():
    allbars={};repairs=[];counts={}
    for tk in TICKERS:
        bars=parse(read_json(REPO/f'backtest/data/{tk}_1m.json'),tk)
        groups=defaultdict(list)
        for b in bars:groups[b.ts.date()].append(b)
        for day,bs in list(groups.items()):
            if len(bs)!=390:
                p=REPO/f'data/cache/stock-{tk}-{day}.json'
                if p.exists():
                    candidate=parse(read_json(p),tk)
                    if len(candidate)==390 and all(b.ts.date()==day for b in candidate):
                        repairs.append(dict(ticker=tk,day=str(day),original=len(bs),replacement=390));groups[day]=candidate
        allbars[tk]=groups;counts[tk]={str(day):len(bs) for day,bs in groups.items()}
    valid=sorted(set.intersection(*[{d for d,bs in g.items() if len(bs)==390} for g in allbars.values()]))
    days=valid[-60:];assert len(days)==60
    prepared={}
    for day in days:
        records=[]
        for tk in TICKERS:
            prior=[b for d,bs in sorted(allbars[tk].items()) if d<day for b in bs][-200:]
            assert len(prior)==200 and all(b.ts.date()<day for b in prior)
            ind=IndicatorSet()
            for b in prior:ind.warm(b)
            bs=allbars[tk][day]
            assert all(bs[i].ts==bs[0].ts+timedelta(minutes=i) for i in range(390))
            for bar in bs:
                ind.update(bar)
                x=dict(price=bar.close,atr=ind.atr.value,vwap=ind.vwap.value,ema9=ind.ema9.value,ema21=ind.ema21.value,ema50=ind.ema50.value)
                records.append((bar,x))
        prepared[day]=sorted(records,key=lambda z:(z[0].ts,z[0].ticker))
    return days,prepared,dict(repairs=repairs,counts=counts,selected_days=[str(d) for d in days])


class OptionCache:
    def __init__(self):self.mem={};self.legacy=None;self.missing=set();self.used=set()
    def get(self,contract,now):
        key=(contract,now.date())
        if key not in self.mem:
            p=REPO/f'data/cache/option-{contract}-{now.date()}.json'
            if p.exists():rows=[(r['t'],r['c']) for r in read_json(p)]
            else:
                if self.legacy is None:self.legacy=read_json(REPO/'backtest/data/opt_cache.json')
                rows=self.legacy.get(contract+'|'+str(now.date()),[])
            parsed={datetime.fromisoformat(t.replace('Z','+00:00')).astimezone(ET)+timedelta(minutes=1):float(c) for t,c in rows}
            times=sorted(parsed);self.mem[key]=(times,[parsed[t] for t in times])
            if not times:self.missing.add(contract+'|'+str(now.date()))
        times,values=self.mem[key];i=bisect.bisect_right(times,now)-1
        if i<0 or now-times[i]>timedelta(minutes=5):return None
        self.used.add(contract+'|'+str(now.date()))
        return values[i],times[i]


def simulate(records,cfg,options=None):
    ctx=dict(latched=cfg['latched'],coordinate=cfg['coordinate'],squeeze=cfg.get('squeeze',False),vwap=cfg.get('vwap',False),floor=cfg.get('floor',False),
             book=DirectionBook(),history=defaultdict(list),vetoes=Counter(),excluded=set())
    settings=Settings(trend_side=cfg['trend']);risk=RiskGate(settings)
    bots=[ReplayBot(tk,spec,TRIGGERS[k](settings.charge_range_atr),settings,context=ctx) for tk in TICKERS for k,spec in BOT_SPECS.items()]
    active={};due={};closed=[];rejected=Counter();offered=0;quote_available=0;streak=0;halt=False;realized=0.;peak=0.;dd=0.;daily_mark=0.;mark_complete=True;maxactive=0;opposing=0
    financial=options is not None;fee=.65;slip=.01
    def get_quote(contract,tk,now):
        got=options.get(contract,now)
        if not got:return None
        px,ended=got;hs=settings.half_spread[tk]
        return Quote(contract,ended,max(.01,round(px-hs,2)),round(px+hs,2))
    for bar,x in records:
        now=bar.end;tk=bar.ticker;ind=snapshot(x);ctx['history'][tk].append((now,x))
        unrealized=0.;marks_valid=True
        if financial:
            for a in active.values():
                q=get_quote(a['contract'],a['ticker'],now)
                if q is None:marks_valid=False;continue
                unrealized+=(max(.01,q.bid-slip)-a['premium'])*a['qty']*100-fee*a['qty']
            if marks_valid:
                daily_mark=realized+unrealized;peak=max(peak,daily_mark);dd=max(dd,peak-daily_mark)
                if daily_mark<=-1500:halt=True;ctx['latched']=True
        for bot in [b for b in bots if b.ticker==tk]:
            # Force account risk reduction while maintaining exit-intent latch.
            if financial and halt and bot.position:bot.exit_reason=bot.exit_reason or 'ACCOUNT_RISK'
            if financial and (halt or streak>=4) and bot.position is None:bot.paused=True
            output=bot.on_bar(bar,ind)
            for intent in output.intents:
                if intent.kind=='BUY_OPEN':
                    offered+=1;qty=intent.qty;contract=occ_symbol(tk,next_trading_day(bar.ts.date()),intent.right,atm_strike(bar.close));premium=1.
                    reject=None
                    if financial:
                        q=get_quote(contract,tk,now)
                        if q is None:reject='MISSING_OPTION_QUOTE'
                        else:
                            quote_available+=1;premium=q.ask+slip
                            # conservative full long-premium exposure incl both fee legs
                            percontract=premium*100+2*fee
                            qty=min(qty,int(800//percontract))
                            reserved=sum(a['premium']*a['qty']*100+fee*a['qty'] for a in active.values())
                            capacity=min(1500+realized-reserved,1500+daily_mark) if marks_valid else 0
                            qty=min(qty,max(0,int(capacity//percontract)))
                            if not marks_valid:reject='UNPRICED_OPEN_POSITION'
                            elif qty<1:reject='RISK_CAPACITY'
                            else:
                                ok,why=risk.check(replace(intent,qty=qty),q,set())
                                if not ok:reject=why
                        if reject:
                            if cfg['coordinate']:ctx['book'].update_entry(bot.token,0,'REJECTED')
                            bot.on_order_failed('BUY_OPEN',reject);rejected[reject]+=1;continue
                    if cfg['coordinate']:
                        ctx['book'].update_entry(bot.token,qty,'FILLED' if qty==intent.qty else 'CANCELLED')
                    active[bot.bot_id]=dict(bot=bot.bot_id,ticker=tk,side=intent.right,entry_time=now.isoformat(),entry_price=bar.close,atr=ind.atr.value,
                                           token=bot.token,contract=contract,qty=qty,premium=premium)
                    bot.position.qty=qty
                    bot.on_fill(Fill(bot.bot_id,'BUY_OPEN',contract,qty,premium,'modeled_cached_bars' if financial else 'state_only',now),ind.as_dict(),fee=fee*qty if financial else 0)
                    if financial:realized-=fee*qty
                else:
                    a=active[bot.bot_id];due.setdefault(bot.bot_id,now+timedelta(minutes=cfg.get('delay',0)))
                    if now<due[bot.bot_id]:bot.on_order_failed('SELL_CLOSE','SCENARIO_DELAY');continue
                    price=1.
                    if financial:
                        q=get_quote(a['contract'],tk,now)
                        if q is None:bot.on_order_failed('SELL_CLOSE','MISSING_OPTION_QUOTE');rejected['EXIT_MISSING_OPTION_QUOTE']+=1;continue
                        price=max(.01,q.bid-slip)
                    sg=1 if a['side']=='CALL' else -1
                    move=sg*(bar.close-a['entry_price'])/a['atr']
                    net=round((price-a['premium'])*a['qty']*100-2*fee*a['qty'],2) if financial else None
                    closed.append(dict(day=str(bar.ts.date()),variant=cfg['name'],track='modeled_option' if financial else 'signal',**a,exit_time=now.isoformat(),exit_price=bar.close,exit_reason=intent.reason,underlying_atr=move,net_pnl=net))
                    if cfg['coordinate']:ctx['book'].reduce(a['token'],a['qty'])
                    bot.on_fill(Fill(bot.bot_id,'SELL_CLOSE',a['contract'],a['qty'],price,'modeled_cached_bars' if financial else 'state_only',now),ind.as_dict(),fee=fee*a['qty'] if financial else 0)
                    if financial:
                        realized+=net+fee*a['qty']
                        if net<0:streak+=1
                        elif net>0:streak=0
                        if realized<=-1500:halt=True;ctx['latched']=True
                    active.pop(bot.bot_id);due.pop(bot.bot_id,None)
            if cfg['coordinate']:assert ctx['book'].invariant()
        maxactive=max(maxactive,len(active))
        if any(len({p['side'] for p in active.values() if p['ticker']==t})>1 for t in TICKERS):opposing+=1
    vals=[t['underlying_atr'] for t in closed]
    # Never label an unresolved independent session as a complete dollar result.
    result=dict(day=str(records[0][0].ts.date()),variant=cfg['name'],track='modeled_option' if financial else 'signal',trades=len(closed),open_positions=len(active),
                sum_atr=sum(vals),mean_atr=statistics.mean(vals) if vals else None,offered_entries=offered,quoted_entries=quote_available,
                net_pnl=round(realized,2) if financial and not active else None,partial_realized=round(realized,2) if financial else None,
                observed_drawdown=round(dd,2) if financial else None,halted=halt or streak>=4,max_positions=maxactive,opposing_steps=opposing,
                vetoes=dict(ctx['vetoes']),rejections=dict(rejected),residuals=list(active.values()))
    assert not cfg['coordinate'] or opposing==0
    if not financial:assert not active
    return result,closed


def variants():
    configs=[]
    for trend in (False,True):
        prefix='ema' if trend else 'cross'
        for label,flags in [('legacy',dict(latched=False,coordinate=False)),('latched',dict(latched=True,coordinate=False)),
                            ('coordinated',dict(latched=True,coordinate=True)),('squeeze',dict(latched=True,coordinate=True,squeeze=True)),
                            ('vwap',dict(latched=True,coordinate=True,vwap=True)),('combined',dict(latched=True,coordinate=True,squeeze=True,vwap=True)),
                            ('atr3',dict(latched=True,coordinate=True,floor=True))]:
            configs.append(dict(name=prefix+'_'+label,trend=trend,**flags))
        for label in ('legacy','latched','combined','atr3'):
            if label=='combined' and trend or label=='atr3' and not trend:continue
            base=next(c for c in configs if c['name']==prefix+'_'+label)
            for delay in (1,2):configs.append(dict(base,name=base['name']+f'_delay{delay}',delay=delay))
    return configs


def block_bootstrap(day_values,reps=2000):
    rng=random.Random(9060);vals=[]
    for _ in range(reps):
        sampled=rng.choices(day_values,k=len(day_values));n=sum(v[1] for v in sampled)
        vals.append(sum(v[0] for v in sampled)/n if n else 0)
    vals.sort();return [vals[int(.025*reps)],vals[int(.975*reps)]]


def main():
    OUT.mkdir(exist_ok=True)
    production={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (REPO/'scalpcity').glob('*.py')}
    days,data,coverage=prepare();configs=variants();options=OptionCache();daily=[];trades=[]
    print(f'60 sessions: {days[0]}..{days[-1]}; {len(configs)} signal variants plus 14 option variants',flush=True)
    for index,day in enumerate(days):
        for cfg in configs:
            d,t=simulate(data[day],cfg);daily.append(d);trades.extend(t)
            if not cfg.get('delay'):
                d,t=simulate(data[day],cfg,options);daily.append(d);trades.extend(t)
        if (index+1)%10==0:print(f'Completed {index+1}/60 sessions',flush=True)
    summaries=[]
    for track in ('signal','modeled_option'):
        for cfg in configs:
            ds=[d for d in daily if d['track']==track and d['variant']==cfg['name']]
            if not ds:continue
            ts=[t for t in trades if t['track']==track and t['variant']==cfg['name']]
            vals=[t['underlying_atr'] for t in ts];complete=[d for d in ds if d['open_positions']==0]
            out=dict(track=track,variant=cfg['name'],sessions=len(ds),trades=len(ts),mean_atr=statistics.mean(vals) if vals else None,
                     total_atr=sum(vals),positive_pct=100*sum(v>0 for v in vals)/len(vals) if vals else None,
                     worst_atr=min(vals) if vals else None,first30_mean=sum(d['sum_atr'] for d in ds[:30])/max(1,sum(d['trades'] for d in ds[:30])),
                     last30_mean=sum(d['sum_atr'] for d in ds[30:])/max(1,sum(d['trades'] for d in ds[30:])),
                     ci95=block_bootstrap([(d['sum_atr'],d['trades']) for d in ds]),
                     mean_after_0_1_atr=statistics.mean(vals)-.1 if vals else None,mean_after_0_2_atr=statistics.mean(vals)-.2 if vals else None,
                     complete_sessions=len(complete),residual_sessions=len(ds)-len(complete),
                     offered_entries=sum(d['offered_entries'] for d in ds),quoted_entries=sum(d['quoted_entries'] for d in ds),
                     complete_session_pnl=sum(d['net_pnl'] for d in complete) if track=='modeled_option' else None,
                     all_session_pnl=sum(d['net_pnl'] for d in ds) if track=='modeled_option' and len(complete)==60 else None)
            summaries.append(out)
    for name,rows in [('daily.csv',daily),('trades.csv',trades),('summary.csv',summaries)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result=dict(coverage=coverage,configs=configs,summary=summaries,daily=daily,
                option_coverage=dict(requested_contract_days=len(options.mem),used_contract_days=len(options.used),missing_contract_days=len(options.missing),missing=sorted(options.missing)))
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    for p,h in production.items():assert hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h
    SOURCES.update([Path(__file__),ROOT/'plan.json',ROOT.parent/'replay/run.py',ROOT.parent/'replay/coordination.py'])
    (OUT/'manifest.json').write_text(json.dumps(dict(sources={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCES)},production=production,production_unchanged=True),indent=2)+'\n')
    print('Finished. Signal zero-delay summaries:')
    for s in summaries:
        if s['track']=='signal' and 'delay' not in s['variant']:print(s['variant'],s['trades'],round(s['mean_atr'],4),s['ci95'])

if __name__=='__main__':main()
