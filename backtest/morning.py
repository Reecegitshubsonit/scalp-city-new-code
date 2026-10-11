"""Morning-only backtest of the 3 Scalp City triggers on 1DTE ATM options. Research script, paper only."""
import json, time, sys, bisect, collections, statistics as st
from datetime import datetime, time as T, timedelta
from zoneinfo import ZoneInfo
import requests
ET=ZoneInfo("America/New_York"); UTC=ZoneInfo("UTC")
ENTRY_START,ENTRY_END,FLAT=T(9,30),T(12,0),T(12,15)   # morning window: entries to 12:00, flat by 12:15
QTY,GOAL,LOSS,COOL=10,600,-100,2
HALF={"SPY":.01,"QQQ":.015,"IWM":.02}
env={}
for l in open('.env'):
    l=l.strip()
    if '=' in l and not l.startswith('#'):
        k,v=l.split('=',1); env[k]=v.strip().strip('"\'')
H={"APCA-API-KEY-ID":env['ALPACA_API_KEY'],"APCA-API-SECRET-KEY":env['ALPACA_SECRET_KEY']}

def load(t):
    out=[]
    for b in json.load(open(f"backtest/data/{t}_1m.json")):
        s=datetime.fromisoformat(b["t"].replace("Z","+00:00")).astimezone(ET)
        if T(9,30)<=s.time()<T(16,0): out.append((s,b["o"],b["h"],b["l"],b["c"],b["v"]))
    return out
class Ema:
    def __init__(s,n): s.k=2/(n+1); s.v=None
    def u(s,x): s.v=x if s.v is None else s.v+s.k*(x-s.v); return s.v
def signals(t,bars):
    """yield per-bar dicts with signals; bots vwap/ema50/range."""
    e9,e21,e50=Ema(9),Ema(21),Ema(50); atr=None; pc=None; n=0
    day=None; pv=vv=0.0; prev={"vwap":None,"ema50":None}; rng_hi=rng_lo=None; inrange_prev=False; out=[]
    for i,(s,o,h,l,c,v) in enumerate(bars):
        d=s.date()
        if d!=day:
            day=d; pv=vv=0.0; prev={"vwap":None,"ema50":None}; rng_hi,rng_lo=-1e9,1e9; inrange_prev=True
        tr=(h-l) if pc is None else max(h-l,abs(h-pc),abs(l-pc)); pc=c; n+=1
        atr=tr if atr is None else (atr*13+tr)/14 if n>14 else (atr*(n-1)+tr)/n
        a9,a21,a50=e9.u(c),e21.u(c),e50.u(c)
        tp=(h+l+c)/3; pv+=tp*v; vv+=v; vwap=pv/vv
        sig={}
        if prev["vwap"] is not None:
            if prev["vwap"]<0<=0 or False: pass
        # crosses: strictly one side to strictly other
        for k,lvl in (("vwap",vwap),("ema50",a50)):
            side=(c>lvl)-(c<lvl)
            p=prev[k]
            if p is not None and side!=0 and p!=0 and side!=p: sig[k]="CALL" if side>0 else "PUT"
            if side!=0: prev[k]=side
            elif p is None: prev[k]=0
        tm=s.time()
        if tm<T(9,45): rng_hi=max(rng_hi,h); rng_lo=min(rng_lo,l)
        else:
            inside=rng_lo<=c<=rng_hi
            if inrange_prev and not inside: sig["range"]="CALL" if c>rng_hi else "PUT"
            inrange_prev=inside
        chop=abs(a9-a21)<0.15*atr
        out.append(dict(i=i,t=s,sig=sig,chop=chop,atr=atr))
    return out

def sim_underlying(t,bars):
    sg=signals(t,bars); trades=[]
    byday=collections.defaultdict(list)
    for x in sg: byday[x["t"].date()].append(x)
    for d,xs in byday.items():
        for bot in ("vwap","ema50","range"):
            pnl_est=0.0; free_at=None; k=0
            while k<len(xs):
                x=xs[k]; end=x["t"]+timedelta(minutes=1)
                sig=x["sig"].get(bot)
                ok = sig and ENTRY_START<=end.time()<=ENTRY_END and not (bot=="vwap" and x["chop"]) \
                     and (bot!="range" or end.time()>=T(9,45)) and (free_at is None or end>=free_at) and k+1<len(xs)
                if not ok: k+=1; continue
                en=bars[xs[k+1]["i"]]; ent_t=en[0]; ent_px=en[1]; atr=x["atr"]
                stop=ent_px-atr if sig=="CALL" else ent_px+atr; tgt=ent_px+2*atr if sig=="CALL" else ent_px-2*atr
                j=k+1; why="TIME"; exit_t=None; exit_px=None
                while j<len(xs):
                    _,o,h,l,c,_v=bars[xs[j]["i"]]; tm=xs[j]["t"]
                    hit_s = l<=stop if sig=="CALL" else h>=stop
                    hit_t = h>=tgt if sig=="CALL" else l<=tgt
                    if hit_s: why,exit_t,exit_px="STOP",tm+timedelta(minutes=1),stop; break
                    if hit_t: why,exit_t,exit_px="TARGET",tm+timedelta(minutes=1),tgt; break
                    if tm.time()>=T(12,14): why,exit_t,exit_px="TIME",tm+timedelta(minutes=1),c; break
                    j+=1
                if exit_t is None: break
                trades.append(dict(tk=t,bot=bot,day=d,dir=sig,ent=ent_t,ext=exit_t,und_in=ent_px,und_out=exit_px,why=why,atr=atr))
                free_at=exit_t+timedelta(minutes=COOL); k=j+1
    return trades

def next_day(d,days):
    i=bisect.bisect_right(days,d)
    if i<len(days): return days[i]
    e=d+timedelta(days=1)
    while e.weekday()>=5: e+=timedelta(days=1)
    return e
def occ(t,exp,right,strike): return f"{t}{exp:%y%m%d}{right}{int(round(strike*1000)):08d}"

def fetch_option_bars(need):
    """need: {(day): set(symbols)} -> {sym: [(ts_et, close)]} cached on disk"""
    import os; cache="backtest/data/opt_cache.json"
    C=json.load(open(cache)) if os.path.exists(cache) else {}
    for d,syms in sorted(need.items()):
        todo=[s for s in syms if f"{s}|{d}" not in C]
        for i in range(0,len(todo),50):
            chunk=todo[i:i+50]
            st_=datetime.combine(d,T(9,30),ET).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            en_=datetime.combine(d,T(12,30),ET).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            p=dict(symbols=",".join(chunk),timeframe="1Min",start=st_,end=en_,limit=10000); got={}
            while True:
                r=requests.get("https://data.alpaca.markets/v1beta1/options/bars",headers=H,params=p)
                if r.status_code==429: time.sleep(10); continue
                if r.status_code!=200: print("ERR",r.status_code,r.text[:150]); break
                j=r.json()
                for s,bs in (j.get("bars") or {}).items(): got.setdefault(s,[]).extend((b["t"],b["c"]) for b in bs)
                if j.get("next_page_token"): p["page_token"]=j["next_page_token"]; continue
                break
            time.sleep(0.4)
            for s in chunk: C[f"{s}|{d}"]=got.get(s,[])
        json.dump(C,open(cache,"w"))
    return C
def px_at(series,ts,maxage=5):
    """last traded close at or before ts (within maxage min)"""
    best=None
    for t,c in series:
        tt=datetime.fromisoformat(t.replace("Z","+00:00")).astimezone(ET)
        if tt<=ts: best=(tt,c)
        else: break
    if best and (ts-best[0])<=timedelta(minutes=maxage): return best[1]
    return None

def main():
    allt=[]; days=set()
    D={}
    for t in ("QQQ","SPY","IWM"):
        D[t]=load(t); days|={b[0].date() for b in D[t]}
    days=sorted(days)
    for t in D: allt+=sim_underlying(t,D[t])
    # need option contract per trade
    need=collections.defaultdict(set)
    for tr in allt:
        tr["exp"]=next_day(tr["day"],days)
        tr["strike"]=round(tr["und_in"]); tr["right"]="C" if tr["dir"]=="CALL" else "P"
        tr["sym"]=occ(tr["tk"],tr["exp"],tr["right"],tr["strike"]); need[tr["day"]].add(tr["sym"])
    print("underlying trades",len(allt),"contract-days",sum(len(v) for v in need.values()),flush=True)
    C=fetch_option_bars(need)
    res=[]; skipped=collections.Counter()
    for tr in allt:
        ser=C.get(f"{tr['sym']}|{tr['day']}",[])
        a=px_at(ser,tr["ent"]+timedelta(minutes=1)); b=px_at(ser,tr["ext"],maxage=10)
        if a is None or b is None: skipped[tr["bot"]]+=1; continue
        h=HALF[tr["tk"]]; buy=a+h; sell=max(b-h,0.01)
        tr["pnl"]=(sell-buy)*100*QTY; tr["buy"]=buy; tr["sell"]=sell; res.append(tr)
    # daily goal/loss lockout per bot (applied in time order)
    res.sort(key=lambda r:(r["tk"],r["bot"],r["day"],r["ent"]))
    kept=[]; cur=None; run=0
    for r in res:
        key=(r["tk"],r["bot"],r["day"])
        if key!=cur: cur=key; run=0
        if run>=GOAL or run<=LOSS: continue
        run+=r["pnl"]; kept.append(r)
    print("skipped (no option quote)",dict(skipped),"kept",len(kept),"of",len(res))
    def rep(rs,label):
        if not rs: print(label,"no trades"); return
        p=[r["pnl"] for r in rs]; w=[x for x in p if x>0]
        sd=st.pstdev(p) or 1; byday=collections.defaultdict(float)
        for r in rs: byday[r["day"]]+=r["pnl"]
        print(f"{label:14s} n={len(p):4d} win={len(w)/len(p):5.1%} total=${sum(p):9.0f} avg=${sum(p)/len(p):7.1f} t={sum(p)/len(p)/(sd/len(p)**.5):5.2f} worstday=${min(byday.values()):7.0f}")
    rep(kept,"ALL")
    for bot in ("vwap","ema50","range"): rep([r for r in kept if r["bot"]==bot],bot)
    for t in ("QQQ","SPY","IWM"): rep([r for r in kept if r["tk"]==t],t)
    for t in ("QQQ","SPY","IWM"):
        for bot in ("vwap","ema50","range"): rep([r for r in kept if r["tk"]==t and r["bot"]==bot],f"{t}-{bot}")
    for w in ("STOP","TARGET","TIME"): rep([r for r in kept if r["why"]==w],"exit "+w)
    json.dump([{**r,"day":str(r["day"]),"ent":str(r["ent"]),"ext":str(r["ext"]),"exp":str(r["exp"])} for r in kept],open("backtest/data/morning_trades.json","w"))
    print("days",days[0],days[-1],len(days))
main()
