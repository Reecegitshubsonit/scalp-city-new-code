"""Where could an edge be? Uses logged signals (logs/*-live.jsonl) and recorded Webull bars (data/webull/<day>/stock-*.json).

Stock-only metrics remove option costs, so they ask: did price move the way the bot bet?
  target%: close reaches +2 ATR before -1 ATR (flat at 15:55). No edge is about 33%.
  r15/r30/rEnd: signed move after the signal, in ATR units, at +15 min, +30 min and 15:55.
  dayT: mean of daily mean r30 divided by its standard error. Trades in one day are not independent.
Actual option P&L comes from trade_closed events. Run from the repo root.
"""
import glob
import json
import math
import os
import random
import statistics as st
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

OUT = "reports/edge-hunt-2026-11-06"
ET = timezone(timedelta(hours=-4))


def et(s):
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(s.replace("+0000", "+00:00")).astimezone(ZoneInfo("America/New_York"))


def load_bars(day, ticker):
    p = f"data/webull/{day}/stock-{ticker}.json"
    if not os.path.exists(p):
        return []
    rows = []
    for b in json.load(open(p)):
        t = et(b["time"])
        if time(9, 30) <= t.time() < time(16, 0):
            rows.append(dict(t=t, o=float(b["open"]), h=float(b["high"]), l=float(b["low"]), c=float(b["close"]), v=float(b["volume"])))
    return sorted(rows, key=lambda x: x["t"])


def outcome(bars, i, sgn, atr):
    entry = bars[i]["c"]
    hit, r = None, {}
    for j in range(i + 1, len(bars)):
        b = bars[j]
        if b["t"].time() >= time(15, 55):
            hit = hit or "TIME"
            r.setdefault("end", sgn * (b["c"] - entry) / atr)
            break
        m = sgn * (b["c"] - entry) / atr
        if hit is None:
            if m <= -1:
                hit = "STOP"
            elif m >= 2:
                hit = "TARGET"
        if j - i == 15:
            r["r15"] = m
        if j - i == 30:
            r["r30"] = m
    return hit or "TIME", r


signals, last_sig, trades = [], {}, []
days = sorted(os.path.basename(f)[:10] for f in glob.glob("logs/*-live.jsonl") if "2026-11-06" not in f)  # today is still running
bars_cache = {}
for day in days:
    last_sig = {}  # a trade must match a signal from its own day
    for t in ("QQQ", "SPY", "IWM"):
        bars_cache[day, t] = load_bars(day, t)
    nth = defaultdict(int)
    for line in open(f"logs/{day}-live.jsonl"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        bot = e.get("bot")
        if e.get("kind") == "state_change" and e.get("reason_code") == "SIGNAL":
            inp = e["inputs"]
            ticker, trig = bot.split("-")
            bars = bars_cache[day, ticker]
            when = datetime.fromisoformat(e["time"])
            idx = next((k for k, b in enumerate(bars) if b["t"] + timedelta(minutes=1) == when), None)
            if idx is None or not inp.get("atr"):
                last_sig.pop(bot, None)
                continue
            price, atr = inp["price"], inp["atr"]
            side = e["reason_text"].split()[0]
            if trig == "RANGE":
                rb = [b for b in bars if b["t"].time() < time(9, 45)]
                cross = "UP" if price > max(b["h"] for b in rb) else "DOWN"
                size = (price - max(b["h"] for b in rb)) if cross == "UP" else (min(b["l"] for b in rb) - price)
            else:
                lvl = inp["vwap"] if trig == "VWAP" else inp["ema50"]
                cross = "UP" if price > lvl else "DOWN"
                size = abs(price - lvl)
            nth[bot] += 1
            s = dict(day=day, ticker=ticker, trig=trig, bot=bot, when=when, idx=idx, price=price, atr=atr, side=side, cross=cross, nth=nth[bot],
                     size=size / atr, trend="UP" if inp["ema9"] > inp["ema21"] else "DOWN",
                     above_vwap=price > inp["vwap"], above50=price > inp["ema50"], pnl=None, spread=None, filled=False)
            for name, sgn_side in (("side", 1 if side == "CALL" else -1), ("cr", 1 if cross == "UP" else -1)):
                hit, r = outcome(bars, idx, sgn_side, atr)
                s["hit_" + name], s["r_" + name] = hit, r
            signals.append(s)
            last_sig[bot] = s
        elif e.get("kind") == "order_sent" and e.get("reason_code") == "BUY_OPEN" and bot in last_sig:
            parts = e["reason_text"].split("bid/ask ")[-1].split("/")
            try:
                last_sig[bot]["spread"] = float(parts[1]) - float(parts[0])
                last_sig[bot]["ask"] = float(parts[1])
            except (ValueError, IndexError):
                pass
        elif e.get("kind") == "trade_closed" and bot in last_sig:
            last_sig[bot]["pnl"] = e["pnl"]
            last_sig[bot]["filled"] = True


def row(name, rows, key="side"):
    n = len(rows)
    if not n:
        return f"{name:<42} n=0"
    tgt = sum(r["hit_" + key] == "TARGET" for r in rows) / n * 100
    def mean(field):
        v = [r["r_" + key][field] for r in rows if field in r["r_" + key]]
        return st.mean(v) if v else float("nan")
    by_day = defaultdict(list)
    for r in rows:
        if "r30" in r["r_" + key]:
            by_day[r["day"]].append(r["r_" + key]["r30"])
    dm = [st.mean(v) for v in by_day.values()]
    dayt = st.mean(dm) / (st.stdev(dm) / math.sqrt(len(dm))) if len(dm) > 2 and st.stdev(dm) > 0 else float("nan")
    tr = [r["pnl"] for r in rows if r["pnl"] is not None]
    pnl = f"{sum(tr):>9.0f} ({sum(tr)/len(tr):>5.0f}/t, {len(tr)}t)" if tr else "        -"
    return f"{name:<42} n={n:<4} days={len(by_day):<3} target%={tgt:5.1f} r15={mean('r15'):+.2f} r30={mean('r30'):+.2f} rEnd={mean('end'):+.2f} dayT={dayt:+.2f} optionPnL={pnl}"


sigs = [s for s in signals if s["day"] != "2026-11-06"]
ud = sorted({s["day"] for s in sigs})
half = ud[len(ud) // 2]
L = [f"Days {ud[0]} to {ud[-1]} ({len(ud)} full days, today excluded). Signals {len(sigs)}, closed trades {sum(s['pnl'] is not None for s in sigs)}.",
     f"Early half = before {half}, late half = from {half}.", ""]


def block(title, cells, key="side"):
    L.append("== " + title)
    for name, f in cells:
        rows = [s for s in sigs if f(s)]
        L.append(row(name, rows, key))
        L.append(row("   early", [s for s in rows if s["day"] < half], key))
        L.append(row("   late", [s for s in rows if s["day"] >= half], key))
    L.append("")


# Placebos: every minute 9:45-15:30, random side and EMA9/21 side.
rng = random.Random(7)
plc = {"random side": [], "EMA9/21 side": []}
for (day, t), bars in bars_cache.items():
    if day == "2026-11-06" or len(bars) < 60:
        continue
    e9 = e21 = None
    atr = None
    prev = None
    for i, b in enumerate(bars):
        e9 = b["c"] if e9 is None else b["c"] * .2 + e9 * .8
        e21 = b["c"] if e21 is None else b["c"] * 2 / 22 + e21 * 20 / 22
        tr = b["h"] - b["l"] if prev is None else max(b["h"] - b["l"], abs(b["h"] - prev), abs(b["l"] - prev))
        atr = tr if atr is None else (atr * 13 + tr) / 14
        prev = b["c"]
        if time(9, 45) <= b["t"].time() <= time(15, 30) and atr > 0:
            for name, sgn in (("random side", rng.choice((1, -1))), ("EMA9/21 side", 1 if e9 > e21 else -1)):
                hit, r = outcome(bars, i, sgn, atr)
                plc[name].append(dict(day=day, hit_side=hit, r_side=r, pnl=None))
L.append("== Placebo: any minute, no signal at all")
for name, rows in plc.items():
    L.append(row(name, rows))
L.append("")

block("All logged signals, side as traded", [("ALL", lambda s: True)] + [(t, lambda s, t=t: s["trig"] == t) for t in ("VWAP", "EMA50", "RANGE")])
block("Your question: side vs where price sits against VWAP (VWAP bots)", [
    ("PUT, price below VWAP (cross down)", lambda s: s["trig"] == "VWAP" and s["side"] == "PUT" and not s["above_vwap"]),
    ("CALL, price above VWAP (cross up)", lambda s: s["trig"] == "VWAP" and s["side"] == "CALL" and s["above_vwap"]),
    ("PUT, price above VWAP (cross up, flipped)", lambda s: s["trig"] == "VWAP" and s["side"] == "PUT" and s["above_vwap"]),
    ("CALL, price below VWAP (cross down, flipped)", lambda s: s["trig"] == "VWAP" and s["side"] == "CALL" and not s["above_vwap"]),
])
block("All triggers: side with the cross or against it", [
    (f"{t} with cross", lambda s, t=t: s["trig"] == t and (s["side"] == "CALL") == (s["cross"] == "UP")) for t in ("VWAP", "EMA50", "RANGE")
] + [
    (f"{t} against cross", lambda s, t=t: s["trig"] == t and (s["side"] == "CALL") != (s["cross"] == "UP")) for t in ("VWAP", "EMA50", "RANGE")
])
block("Pure cross direction, ignoring EMA9/21 (stock only; P&L column is as traded)", [(t, lambda s, t=t: s["trig"] == t) for t in ("VWAP", "EMA50", "RANGE")], key="cr")
block("Nth signal of the day per bot, side as traded", [
    ("1st signal", lambda s: s["nth"] == 1), ("2nd-3rd", lambda s: 2 <= s["nth"] <= 3), ("4th+", lambda s: s["nth"] >= 4),
    ("RANGE 1st signal", lambda s: s["trig"] == "RANGE" and s["nth"] == 1), ("RANGE 2nd+", lambda s: s["trig"] == "RANGE" and s["nth"] > 1),
])
block("RANGE break direction and size", [
    ("Up break", lambda s: s["trig"] == "RANGE" and s["cross"] == "UP"), ("Down break", lambda s: s["trig"] == "RANGE" and s["cross"] == "DOWN"),
    ("Break >= 0.5 ATR", lambda s: s["trig"] == "RANGE" and s["size"] >= .5), ("Break < 0.5 ATR", lambda s: s["trig"] == "RANGE" and s["size"] < .5),
])
block("Time of day (ET)", [
    ("09:30-09:59", lambda s: s["when"].time() < time(10)), ("10:00-11:29", lambda s: time(10) <= s["when"].time() < time(11, 30)),
    ("11:30-13:59", lambda s: time(11, 30) <= s["when"].time() < time(14)), ("14:00+", lambda s: s["when"].time() >= time(14)),
])
block("All three agree: side, side of VWAP and side of EMA50", [
    ("Aligned CALL (above VWAP, above EMA50)", lambda s: s["side"] == "CALL" and s["above_vwap"] and s["above50"]),
    ("Aligned PUT (below VWAP, below EMA50)", lambda s: s["side"] == "PUT" and not s["above_vwap"] and not s["above50"]),
    ("Not aligned", lambda s: not ((s["side"] == "CALL" and s["above_vwap"] and s["above50"]) or (s["side"] == "PUT" and not s["above_vwap"] and not s["above50"]))),
])
block("By ticker", [(t, lambda s, t=t: s["ticker"] == t) for t in ("QQQ", "SPY", "IWM")])

# Costs: entry spread against the size of the stock move the trade is playing for.
c = [s for s in sigs if s["spread"] is not None and s["pnl"] is not None]
L.append("== Option cost against the stock move")
for t in ("QQQ", "SPY", "IWM"):
    v = [s for s in c if s["ticker"] == t]
    sp = st.mean(s["spread"] for s in v)
    L.append(f"{t}: trades {len(v)}, mean entry spread ${sp:.3f} = ${sp*1000:.0f} per 10 contracts, mean ATR ${st.mean(s['atr'] for s in v):.3f}, mean ask ${st.mean(s['ask'] for s in v):.2f}, "
             f"spread / (0.5 delta x 1 ATR) = {st.mean(s['spread'] / (0.5 * s['atr']) for s in v) * 100:.0f}%")
o = sorted(c, key=lambda s: s["spread"] / s["atr"])
k = len(o) // 3
for name, part in (("Cheapest third (spread/ATR)", o[:k]), ("Middle third", o[k:2 * k]), ("Costliest third", o[2 * k:])):
    L.append(row(name, part))
L.append("")

# Target-rate stability per day, side as traded.
L.append("== Per day, side as traded")
for d in ud:
    L.append(row(d, [s for s in sigs if s["day"] == d]))

open(f"{OUT}/results.txt", "w").write("\n".join(L) + "\n")
with open(f"{OUT}/signals.csv", "w") as f:
    cols = "day when bot side cross trend above_vwap above50 nth size atr spread hit_side hit_cr pnl".split()
    f.write(",".join(cols) + "\n")
    for s in sigs:
        f.write(",".join(str(s.get(x)) for x in cols) + "\n")
print("\n".join(L))
