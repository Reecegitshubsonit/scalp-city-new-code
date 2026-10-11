"""Entry-edge analysis, 2026-10-09. Research only: reads backtest/data and logs, no network, no broker, no .env.
Run from repo root:  python3 reports/analysis-2026-10-09/analyze.py
Writes reports/analysis-2026-10-09/{results.json,output.txt}.

Simulator mirrors the live engine (scalpcity/bot.py, triggers.py, indicators.py):
  - RTH 1-min bars; EMA9/21/50 and Wilder ATR14 carried across days; VWAP resets daily
  - level cross: prev_close vs prev_level -> close vs level; range = 9:30-9:44 hi/lo, signal on close leaving it
  - entry at the signal bar's close; stop 1 ATR / target 2 ATR from that close
  - exits checked on BAR CLOSE (live parity) and filled at that close; flat at bar end >= 15:55
  - cooldown 120 s after an exit; entries for bar end in [window start, 15:30]; VWAP bot skips EMA9/21 squeeze
  - no daily goal/loss lock (today's run evidently did not enforce the $100 lock either)
Intrabar touch exits are a sensitivity only.
"""
import json, collections, itertools, math, random, re, statistics as st, sys
from datetime import datetime, time as T, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
TICKERS = ("SPY", "QQQ", "IWM")
BOTS = ("vwap", "ema50", "range")
OUT = "reports/analysis-2026-10-09/"
QTY, DELTA, FEE_SIDE = 10, 0.5, 0.04          # contracts, ATM delta, $ regulatory fees per contract per side
SPREADS = (0.01, 0.02, 0.03)                   # full bid/ask width as fraction of premium, paid once per round trip
SEL_SPREAD = 0.02
WINDOWS = {"W0 9:30-15:30": (T(9, 30), T(15, 30)), "W1 10:00-15:30": (T(10, 0), T(15, 30)),
           "W2 9:30-12:00": (T(9, 30), T(12, 0)), "W3 10:00-14:00": (T(10, 0), T(14, 0))}
FLAGS = ("buffer", "trend", "chop_all", "dedupe", "stopcool", "")[:5]
STOP_COOL_MIN = 15
lines = []


def P(*a):
    s = " ".join(str(x) for x in a); print(s); lines.append(s)


# ---------------- data ----------------
def load(t):
    out = []
    for b in json.load(open(f"backtest/data/{t}_1m.json")):
        s = datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET)
        if T(9, 30) <= s.time() < T(16, 0):
            out.append((s, b["o"], b["h"], b["l"], b["c"], b["v"]))
    return out


class Ema:
    def __init__(s, n): s.k = 2 / (n + 1); s.v = None; s.n = 0
    def u(s, x): s.v = x if s.v is None else s.k * x + (1 - s.k) * s.v; s.n += 1; return s.v


def prepare(bars):
    e9, e21, e50 = Ema(9), Ema(21), Ema(50); atr = None; pc = None; n = 0; trs = []
    day = None; pv = vv = 0.0; prev = {}; hi = lo = None; rprev = None
    days = collections.OrderedDict()
    for (s, o, h, l, c, v) in bars:
        if s.date() != day:
            day = s.date(); pv = vv = 0.0; prev = {"vwap": None, "ema50": None}; hi = lo = None; rprev = None
            days[day] = []
        tr = (h - l) if pc is None else max(h - l, abs(h - pc), abs(l - pc)); pc = c; n += 1
        if n <= 14: trs.append(tr); atr = sum(trs) / len(trs)
        else: atr = (atr * 13 + tr) / 14
        a9, a21, a50 = e9.u(c), e21.u(c), e50.u(c)
        tp = (h + l + c) / 3; pv += tp * v; vv += v; vwap = pv / vv if vv else tp
        r = dict(t=s, end=s + timedelta(minutes=1), h=h, l=l, c=c, atr=atr, e9=a9, e21=a21, sig={}, dist={})
        for k, lvl in (("vwap", vwap), ("ema50", a50 if e50.n >= 50 else None)):
            if lvl is None: continue
            p = prev[k]
            if p is not None:
                if p[0] < p[1] and c > lvl: r["sig"][k] = "CALL"
                elif p[0] > p[1] and c < lvl: r["sig"][k] = "PUT"
            r["dist"][k] = abs(c - lvl) / atr if atr else 0.0
            prev[k] = (c, lvl)
        if s.time() < T(9, 45):
            hi = h if hi is None else max(hi, h); lo = l if lo is None else min(lo, l); rprev = c
        elif hi is not None:
            pin = rprev is not None and lo <= rprev <= hi
            if pin and c > hi: r["sig"]["range"] = "CALL"; r["dist"]["range"] = (c - hi) / atr
            elif pin and c < lo: r["sig"]["range"] = "PUT"; r["dist"]["range"] = (lo - c) / atr
            rprev = c
        days[day].append(r)
    return days


# ---------------- premium model ----------------
def tmin(ts):   # effective minutes of variance left to a next-day expiry: rest of today + 390 + ~120 overnight
    rest = max(0, (datetime.combine(ts.date(), T(16, 0), ET) - ts).total_seconds() / 60)
    return rest + 390 + 120


def premium_model():
    """Per ticker-day k so that ATM mid ~= k * S * sqrt(Tmin), from cached option closes of morning trades."""
    HALF = {"SPY": .01, "QQQ": .015, "IWM": .02}
    ks = collections.defaultdict(list)
    for r in json.load(open("backtest/data/morning_trades.json")):
        ent = datetime.fromisoformat(r["ent"])
        mid = r["buy"] - HALF[r["tk"]]
        if mid > 0.05: ks[(r["tk"], r["day"])].append(mid / (r["und_in"] * math.sqrt(tmin(ent + timedelta(minutes=1)))))
    byday = {k: st.median(v) for k, v in ks.items()}
    bytk = {t: st.median([v for (tt, d), v in byday.items() if tt == t]) for t in TICKERS}
    return byday, bytk


# ---------------- simulator ----------------
def simulate(D, cfg, intrabar=False):
    w0, w1 = WINDOWS[cfg["win"]]
    trades = []
    for t in TICKERS:
        for day, xs in D[t].items():
            pos = {}; free = {b: None for b in BOTS}
            for k, x in enumerate(xs):
                end = x["end"]
                # manage open positions first (exits on this bar)
                for b in list(pos):
                    p = pos[b]
                    if k <= p["k"]: continue
                    sg = 1 if p["dir"] == "CALL" else -1; why = None; px = x["c"]
                    if end.time() >= T(15, 55): why = "TIME"
                    elif intrabar and (x["l"] <= p["stop"] if sg > 0 else x["h"] >= p["stop"]): why, px = "STOP", p["stop"]
                    elif intrabar and (x["h"] >= p["tgt"] if sg > 0 else x["l"] <= p["tgt"]): why, px = "TARGET", p["tgt"]
                    elif not intrabar and sg * (x["c"] - p["stop"]) <= 0: why = "STOP"
                    elif not intrabar and sg * (x["c"] - p["tgt"]) >= 0: why = "TARGET"
                    elif k == len(xs) - 1: why = "EOD"
                    if why:
                        R = sg * (px - p["ent"]) / p["atr"]
                        trades.append(dict(t=t, bot=b, day=day, dir=p["dir"], R=R, why=why, et=p["et"],
                                           hold=(end - p["et"]).total_seconds() / 60, atr=p["atr"], S=p["ent"],
                                           dS=sg * (px - p["ent"])))
                        del pos[b]
                        cool = STOP_COOL_MIN if (cfg["stopcool"] and why == "STOP") else 2
                        free[b] = end + timedelta(minutes=cool)
                # entries
                if end.time() < max(w0, T(9, 31)) or end.time() > w1: continue
                chop = abs(x["e9"] - x["e21"]) < 0.15 * x["atr"]
                for b in BOTS:
                    if b in pos or (free[b] and end < free[b]): continue
                    d = x["sig"].get(b)
                    if not d: continue
                    if (b == "vwap" or cfg["chop_all"]) and chop: continue
                    if cfg["buffer"] and x["dist"].get(b, 0) < 0.2: continue
                    if cfg["trend"] and (d == "CALL") != (x["e9"] > x["e21"]): continue
                    if cfg["dedupe"] and pos: continue
                    sg = 1 if d == "CALL" else -1
                    pos[b] = dict(k=k, dir=d, ent=x["c"], atr=x["atr"], stop=x["c"] - sg * x["atr"],
                                  tgt=x["c"] + 2 * sg * x["atr"], et=end)
    return trades


def add_dollars(trades, byday, bytk):
    for x in trades:
        kk = byday.get((x["t"], str(x["day"])), bytk[x["t"]])
        prem = kk * x["S"] * math.sqrt(tmin(x["et"]))
        x["prem"] = prem
        x["gross"] = QTY * 100 * DELTA * x["dS"]
        theta = prem / (2 * tmin(x["et"])) * x["hold"]          # dP/dt = P/(2T) for ATM
        x["theta"] = QTY * 100 * theta
        x["net"] = {s: x["gross"] - x["theta"] - QTY * 100 * s * prem - 2 * QTY * FEE_SIDE for s in SPREADS}
        dollar_per_R = QTY * 100 * DELTA * x["atr"]
        x["costR"] = {s: (x["gross"] - x["net"][s]) / dollar_per_R for s in SPREADS}


# ---------------- stats ----------------
def summ(tr, s=SEL_SPREAD, boot=0, seed=1):
    if not tr: return dict(n=0)
    n = len(tr); R = [x["R"] for x in tr]
    res = dict(n=n, days=len({x["day"] for x in tr}), win=sum(1 for r in R if r > 0) / n,
               grossR=st.mean(R), netR=st.mean(r - x["costR"][s] for r, x in zip(R, tr)),
               gross=st.mean(x["gross"] for x in tr), net=st.mean(x["net"][s] for x in tr),
               costR=st.mean(x["costR"][s] for x in tr))
    if boot:
        byd = collections.defaultdict(list)
        for x in tr: byd[x["day"]].append(x["net"][s])
        keys = list(byd); rng = random.Random(seed); ms = []
        for _ in range(boot):
            smp = [byd[rng.choice(keys)] for _ in keys]
            tot = sum(sum(v) for v in smp); cnt = sum(len(v) for v in smp)
            ms.append(tot / cnt)
        ms.sort(); res["ci"] = (ms[int(.025 * boot)], ms[int(.975 * boot)])
        res["p_pos"] = sum(1 for m in ms if m > 0) / boot
        dl = [sum(v) for v in byd.values()]; res["per_day"] = st.mean(dl)
    return res


def fmt(r):
    if not r.get("n"): return "no trades"
    s = (f"n={r['n']:5d} win={100*r['win']:4.1f}% grossR={r['grossR']:+.3f} netR={r['netR']:+.3f} "
         f"gross$={r['gross']:+7.1f} net$={r['net']:+7.1f}")
    if "ci" in r: s += f" 95%CI(day-cluster)=[{r['ci'][0]:+.1f},{r['ci'][1]:+.1f}] $/day={r['per_day']:+.0f}"
    return s


def scopes():
    yield "all", lambda x: True, True
    for b in BOTS: yield f"trig:{b}", (lambda b: lambda x: x["bot"] == b)(b), False
    for t in TICKERS: yield f"tk:{t}", (lambda t: lambda x: x["t"] == t)(t), True
    for t in TICKERS:
        for b in BOTS: yield f"{t}-{b}", (lambda t, b: lambda x: x["t"] == t and x["bot"] == b)(t, b), False


def cfgname(c):
    f = [k for k in FLAGS if c[k]]
    return (c["win"].split()[0]) + ":" + ("+".join(f) if f else "base")


# ---------------- live trades ----------------
def live_trades():
    E = [json.loads(l) for l in open("logs/2026-10-09-live.jsonl")]
    BA = re.compile(r"bid/ask ([\d.]+)/([\d.]+)")
    cur = {}; closed = []; failed = 0
    for e in E:
        b = e["bot"]; k = e["kind"]; c = e["reason_code"]
        if k == "order_sent":
            m = BA.search(e["reason_text"]); cur.setdefault(b, {}).setdefault("q", {})[c] = (float(m[1]), float(m[2]), e["inputs"], e["time"])
            if c == "BUY_OPEN": cur[b]["sig_inputs"] = e["inputs"]; cur[b]["sig_time"] = e["time"]
        if k == "state_change" and c == "ORDER_FAILED" and b in cur and "entry" not in cur[b]: cur.pop(b); failed += 1
        if k == "fill" and c == "ENTRY_FILL": cur[b]["entry"] = e
        if k == "fill" and c == "EXIT_FILL": cur[b]["exit"] = e
        if k == "trade_closed":
            x = cur.pop(b); x["closed"] = e; x["bot"] = b; closed.append(x)
    out = []
    for x in closed:
        bi, ai, inp, ti = x["q"]["BUY_OPEN"]; bo, ao, inp2, to = x["q"]["SELL_CLOSE"]
        tk, bot = x["bot"].split("-"); bot = bot.lower()
        side = "CALL" if x["entry"]["contract"][len(tk) + 6] == "C" else "PUT"
        sg = 1 if side == "CALL" else -1; atr = inp["atr"]
        out.append(dict(t=tk, bot=bot, dir=side, time=ti, exit_time=to, inp=inp, atr=atr,
                        R=sg * (inp2["price"] - inp["price"]) / atr, why=x["closed"]["reason_code"],
                        why2=x["exit"]["reason_text"], recorded=x["closed"]["pnl"],
                        quote=(bo - ai) * QTY * 100, midmid=((bo + ao) / 2 - (bi + ai) / 2) * QTY * 100,
                        spread_in=(ai - bi) / ((ai + bi) / 2), prem=(ai + bi) / 2))
    return out, failed, E[-1]["time"]


def live_filter(trades, cfg):
    """Apply entry filters to today's actual trades using logged signal-bar inputs (no new trades can be created)."""
    w0, w1 = WINDOWS[cfg["win"]]; kept = []; open_until = {}; stop_until = {}
    for x in sorted(trades, key=lambda x: x["time"]):
        inp = x["inp"]; tm = datetime.fromisoformat(x["time"]); a = inp["atr"]
        if not (w0 <= tm.time() <= w1): continue
        if cfg["chop_all"] and abs(inp["ema9"] - inp["ema21"]) < 0.15 * a: continue
        if cfg["trend"] and (x["dir"] == "CALL") != (inp["ema9"] > inp["ema21"]): continue
        if cfg["buffer"]:
            lvl = inp["vwap"] if x["bot"] == "vwap" else inp["ema50"] if x["bot"] == "ema50" else None
            if lvl is not None and abs(inp["price"] - lvl) / a < 0.2: continue
            if lvl is None and (x["inp"].get("distance_atr") or 0) == 0 and False: continue
        if cfg["dedupe"] and any(u > tm for (tk, b), u in open_until.items() if tk == x["t"]): continue
        if cfg["stopcool"] and stop_until.get((x["t"], x["bot"])) and tm < stop_until[(x["t"], x["bot"])]: continue
        kept.append(x)
        te = datetime.fromisoformat(x["exit_time"])
        open_until[(x["t"], x["bot"])] = te
        if "STOP" in x["why2"] or x["recorded"] < 0: stop_until[(x["t"], x["bot"])] = te + timedelta(minutes=STOP_COOL_MIN)
    return kept


# ---------------- main ----------------
def main():
    D = {t: prepare(load(t)) for t in TICKERS}
    days = sorted(set(D["SPY"]) & set(D["QQQ"]) & set(D["IWM"]))
    for t in TICKERS: D[t] = collections.OrderedDict((d, v) for d, v in D[t].items() if d in days)
    byday, bytk = premium_model()
    train, val, hold = set(days[:50]), set(days[50:70]), set(days[70:])
    P(f"days {days[0]}..{days[-1]} n={len(days)}; train {min(train)}..{max(train)} ({len(train)}), "
      f"validation {min(val)}..{max(val)} ({len(val)}), HOLDOUT {min(hold)}..{max(hold)} ({len(hold)})")
    P(f"premium model k=P/(S*sqrt(Tmin)) per ticker median: " + ", ".join(f"{t} {bytk[t]:.5f}" for t in TICKERS))

    # ---- live trades ----
    LT, failed, last = live_trades()
    P(f"\n=== LIVE 2026-10-09 (log through {last}): {len(LT)} closed trades, {failed} entries not filled ===")
    P("quoted spread at entry, % of mid: " + ", ".join(
        f"{t} median {100*st.median([x['spread_in'] for x in LT if x['t']==t]):.2f}% max {100*max([x['spread_in'] for x in LT if x['t']==t]):.2f}%" for t in TICKERS))
    kfit = {t: st.median([x["prem"] / (x["inp"]["price"] * math.sqrt(tmin(datetime.fromisoformat(x["time"])))) for x in LT if x["t"] == t]) for t in TICKERS}
    P("live k (same model): " + ", ".join(f"{t} {kfit[t]:.5f}" for t in TICKERS) + "  (compare to historical medians above)")
    def lsum(xs):
        if not xs: return "none"
        n = len(xs)
        return (f"n={n:3d} win={100*sum(1 for x in xs if x['recorded']>0)/n:4.0f}% und-R/trade={st.mean(x['R'] for x in xs):+.2f} "
                f"recorded$={sum(x['recorded'] for x in xs):+6.0f} ({st.mean(x['recorded'] for x in xs):+5.0f}/tr) "
                f"mid-mid$={sum(x['midmid'] for x in xs):+6.0f} ask-in/bid-out$={sum(x['quote'] for x in xs):+6.0f} ({st.mean(x['quote'] for x in xs):+5.0f}/tr)")
    P("ALL      " + lsum(LT))
    for b in BOTS: P(f"{b:8s} " + lsum([x for x in LT if x["bot"] == b]))
    for t in TICKERS: P(f"{t:8s} " + lsum([x for x in LT if x["t"] == t]))
    for t in TICKERS:
        for b in BOTS: P(f"{t}-{b:6s} " + lsum([x for x in LT if x["t"] == t and x["bot"] == b]))
    # dollar-model check on live trades: predicted mid-mid = 1000*0.5*dS - theta
    errs = []
    for x in LT:
        tm = datetime.fromisoformat(x["time"]); te = datetime.fromisoformat(x["exit_time"])
        pred = QTY * 100 * DELTA * x["R"] * x["atr"] - QTY * 100 * x["prem"] / (2 * tmin(tm)) * (te - tm).total_seconds() / 60
        errs.append((pred, x["midmid"]))
    P(f"dollar model check on live: sum predicted mid-mid {sum(p for p,_ in errs):+.0f} vs actual mid-mid {sum(a for _,a in errs):+.0f}; "
      f"corr {st.correlation([p for p,_ in errs],[a for _,a in errs]):.2f}")

    # ---- simulate all configs ----
    cfgs = []
    for win in WINDOWS:
        for bits in itertools.product((0, 1), repeat=5):
            cfgs.append(dict(win=win, **dict(zip(FLAGS, bits))))
    sims = {}
    for i, c in enumerate(cfgs):
        tr = simulate(D, c); add_dollars(tr, byday, bytk); sims[cfgname(c)] = (c, tr)
    base = sims["W0:base"][1]
    P(f"\nsimulated {len(cfgs)} filter configurations (5 binary fixes x 4 windows)")
    P(f"cost in R at 1/2/3% spread (baseline mean incl. theta+fees): " + "/".join(f"{st.mean(x['costR'][s] for x in base):.2f}" for s in SPREADS)
      + f"; mean modelled premium {st.mean(x['prem'] for x in base):.2f}, mean hold {st.mean(x['hold'] for x in base):.1f} min")

    # ---- 1. per-trigger / per-ticker baseline, all data ----
    P("\n=== 1. BASELINE (live rules, bar-close exits), ALL 90 days, net at 2% spread unless stated ===")
    for name, f, _ in scopes():
        P(f"{name:12s} " + fmt(summ([x for x in base if f(x)], boot=1000 if name == 'all' or name.startswith('trig') or name.startswith('tk') else 0)))
    for s in SPREADS:
        r = summ(base, s=s); P(f"  all @ spread {int(s*100)}%: netR={r['netR']:+.3f} net$/trade={r['net']:+.1f}")
    r0 = summ(base, s=0.0) if False else None
    zero = st.mean(x["gross"] - x["theta"] for x in base)
    P(f"  all with ZERO spread, theta only: {zero:+.1f} $/trade; gross (no theta/spread) {st.mean(x['gross'] for x in base):+.1f}")
    ib = simulate(D, sims["W0:base"][0], intrabar=True); add_dollars(ib, byday, bytk)
    P("  sensitivity, intrabar touch exits (optimistic): " + fmt(summ(ib)))
    P("  exit mix (bar-close): " + str(collections.Counter(x["why"] for x in base)))

    # ---- 2. each fix alone and combined, on DEVELOPMENT data only (train+validation) ----
    dev = train | val
    P("\n=== 2. FIXES alone and combined, DEVELOPMENT days only (train+validation, 70 days), all bots, net @2% ===")
    order = ["W0:base", "W0:buffer", "W0:trend", "W0:chop_all", "W0:dedupe", "W0:stopcool",
             "W1:base", "W2:base", "W3:base", "W0:buffer+trend+chop_all", "W0:buffer+trend+chop_all+dedupe+stopcool",
             "W1:buffer+trend+chop_all+dedupe+stopcool", "W2:buffer+trend+chop_all+dedupe+stopcool", "W3:buffer+trend+chop_all+dedupe+stopcool"]
    for nm in order:
        tr = [x for x in sims[nm][1] if x["day"] in dev]
        P(f"{nm:44s} " + fmt(summ(tr, boot=1000)))
    P("per trigger, all five fixes, W0, dev:")
    for b in BOTS:
        P(f"   {b:6s} " + fmt(summ([x for x in sims['W0:buffer+trend+chop_all+dedupe+stopcool'][1] if x['day'] in dev and x['bot'] == b])))

    # ---- 3. selection protocol ----
    P("\n=== 3. SELECTION: rank on train, confirm on validation, holdout once ===")
    cands = []; seen = set()
    for nm, (c, tr) in sims.items():
        for sname, f, multi in scopes():
            if c["dedupe"] and not multi: continue            # dedupe is a no-op for single-bot scopes
            key = (nm, sname); seen.add(key)
            tt = [x for x in tr if f(x) and x["day"] in train]
            if len(tt) < 100: continue
            cands.append((nm, sname, f, tr, summ(tt)))
    P(f"candidates tried: {len(seen)} distinct (config x scope); {len(cands)} had >=100 train trades")
    pos_train = [cnd for cnd in cands if cnd[4]["net"] > 0]
    P(f"candidates with positive NET $/trade on train @2%: {len(pos_train)}")
    cands.sort(key=lambda z: -z[4]["net"])
    P("top 10 on train (net $/trade @2%):")
    for nm, sname, f, tr, r in cands[:10]:
        rv = summ([x for x in tr if f(x) and x["day"] in val])
        P(f"  {nm:40s} {sname:11s} train {fmt(r)}\n  {'':52s} valid {fmt(rv)}")
    # pick: best validation net among top 10 train, provided validation n >= 30
    top = []
    for nm, sname, f, tr, r in cands[:10]:
        rv = summ([x for x in tr if f(x) and x["day"] in val])
        if rv.get("n", 0) >= 30: top.append((rv["net"], nm, sname, f, tr))
    top.sort(key=lambda z: -z[0])
    pick = top[0]
    P(f"SELECTED (best validation among train top-10): {pick[1]} / {pick[2]} (validation net {pick[0]:+.1f} $/trade)")
    gross_pos_train = sum(1 for cnd in cands if cnd[4]["grossR"] > 0)
    P(f"(for reference: {gross_pos_train} of {len(cands)} candidates have positive GROSS R on train)")

    # ---- holdout, reported once ----
    P("\n=== HOLDOUT (20 final days, untouched until now), day-cluster bootstrap 95% CI on net $/trade ===")
    held = {}
    for label, nm, f in (("selected", pick[1], pick[3]), ("baseline live rules", "W0:base", lambda x: True),
                         ("pre-specified audit combo (buffer+trend+chop_all)", "W0:buffer+trend+chop_all", lambda x: True),
                         ("all five fixes, W0", "W0:buffer+trend+chop_all+dedupe+stopcool", lambda x: True)):
        tr = [x for x in sims[nm][1] if f(x) and x["day"] in hold]
        for s in SPREADS:
            r = summ(tr, s=s, boot=2000)
            held[(label, s)] = r
            P(f"{label:52s} @{int(s*100)}% {fmt(r)}  P(mean>0)={r.get('p_pos',0):.2f}")
        rg = summ(tr); P(f"{'':52s} gross R {rg['grossR']:+.3f} (before any option cost)")
    P("\n=== LIVE day as extra out-of-sample: today's actual trades that each filter would have kept ===")
    for nm in ("W0:base", "W0:buffer", "W0:trend", "W0:chop_all", "W0:dedupe", "W0:stopcool", "W1:base", "W2:base", "W3:base",
               "W0:buffer+trend+chop_all", "W0:buffer+trend+chop_all+dedupe+stopcool", pick[1]):
        k = live_filter(LT, sims[nm][0])
        if pick[2] != "all" and nm == pick[1]:
            k = [x for x in k if (pick[2].startswith("trig:") and x["bot"] == pick[2][5:]) or (pick[2].startswith("tk:") and x["t"] == pick[2][3:])
                 or (pick[2] == f"{x['t']}-{x['bot']}")]
            nm += f" [{pick[2]}]"
        P(f"{nm:52s} " + lsum(k))
    P("(live filter replay cannot add trades the live bots skipped, e.g. signals blocked by a position that a filter would have removed; range-bot buffer not checkable from logs)")
    json.dump({"lines": lines}, open(OUT + "results.json", "w"), indent=0, default=str)
    open(OUT + "output.txt", "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
