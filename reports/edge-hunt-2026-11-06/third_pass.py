"""Third pass. Run from the repo root.
1. Reproduce the logged 09:31 VWAP as: prior session's last N bars plus today's 09:30 bar (the suspected feed leak).
2. Stock-only test of the rules as designed, from recorded RTH bars with a true session VWAP. No option costs.
   target%: close reaches +2 ATR before -1 ATR (flat at 15:55). Placebo for the same exit: see results.txt (random side 37.5%).
   dayT: mean of daily mean r30 over its standard error.
"""
import glob
import json
import math
import os
import statistics as st
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
days = sorted(os.path.basename(f)[:10] for f in glob.glob("logs/*-live.jsonl") if "2026-11-06" not in f)
half = days[len(days) // 2]
L = []


def load(day, t):
    p = f"data/webull/{day}/stock-{t}.json"
    if not os.path.exists(p):
        return []
    rows = []
    for b in json.load(open(p)):
        ts = datetime.fromisoformat(b["time"].replace("+0000", "+00:00")).astimezone(NY)
        if time(9, 30) <= ts.time() < time(16):
            rows.append(dict(t=ts, h=float(b["high"]), l=float(b["low"]), c=float(b["close"]), v=float(b["volume"])))
    return sorted(rows, key=lambda x: x["t"])


def typical(b):
    return (b["h"] + b["l"] + b["c"]) / 3


L.append("== 1. Logged first VWAP vs rebuild from prior session's last N bars + today's 09:30 bar")
hits = defaultdict(int)
tested = 0
for prev, day in zip(days, days[1:]):
    first = {}
    for line in open(f"logs/{day}-live.jsonl"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        b = e.get("bot") or ""
        if b.endswith("-VWAP") and (e.get("inputs") or {}).get("vwap") and e.get("time", "").endswith("09:31:00-04:00") or (b.endswith("-VWAP") and (e.get("inputs") or {}).get("vwap") and "T09:31:00" in e.get("time", "")):
            first.setdefault(b.split("-")[0], e["inputs"]["vwap"])
    for t, logged in first.items():
        a, c = load(prev, t), load(day, t)
        if not a or not c:
            continue
        tested += 1
        best = None
        for n in range(0, 4):
            bars = a[-n:] + c[:1] if n else c[:1]
            v = sum(typical(x) * x["v"] for x in bars) / sum(x["v"] for x in bars)
            if abs(v - logged) < 0.02:
                best = n
                break
        hits[best] += 1
        if t == "QQQ" and day == days[-1]:
            L.append(f"example {day} {t}: logged {logged}, 09:30 bar alone {typical(c[0]):.3f}, with prior last 2 bars {sum(typical(x) * x['v'] for x in a[-2:] + c[:1]) / sum(x['v'] for x in a[-2:] + c[:1]):.3f}; prior 15:59 volume {a[-1]['v']:.0f}, 09:30 volume {c[0]['v']:.0f}")
L.append(f"ticker-days tested {tested}; number of prior bars that reproduces logged VWAP within 2c: {dict(hits)} (None = no match)")
L.append("")


def outcome(bars, i, sgn, atr):
    entry = bars[i]["c"]
    hit, r = None, {}
    for j in range(i + 1, len(bars)):
        if bars[j]["t"].time() >= time(15, 55):
            r["end"] = sgn * (bars[j]["c"] - entry) / atr
            break
        m = sgn * (bars[j]["c"] - entry) / atr
        if hit is None:
            hit = "STOP" if m <= -1 else "TARGET" if m >= 2 else None
        if j - i == 15:
            r["r15"] = m
        if j - i == 30:
            r["r30"] = m
    return hit or "TIME", r


rows = []
for day in days:
    for t in ("QQQ", "SPY", "IWM"):
        bars = load(day, t)
        if len(bars) < 60:
            continue
        pv = v = 0.0
        vw = []
        atr = prev = None
        e9 = e21 = None
        hi = lo = None
        first_break = None
        faded = False
        for i, b in enumerate(bars):
            pv += typical(b) * b["v"]
            v += b["v"]
            vw.append(pv / v)
            tr = b["h"] - b["l"] if prev is None else max(b["h"] - b["l"], abs(b["h"] - prev), abs(b["l"] - prev))
            atr = tr if atr is None else (atr * 13 + tr) / 14
            e9 = b["c"] if e9 is None else b["c"] * .2 + e9 * .8
            e21 = b["c"] if e21 is None else b["c"] * 2 / 22 + e21 * 20 / 22
            clock = b["t"].time()
            if clock < time(9, 45):
                hi = b["h"] if hi is None else max(hi, b["h"])
                lo = b["l"] if lo is None else min(lo, b["l"])
            if not atr or clock > time(15, 30) or i == 0:
                prev = b["c"]
                continue
            bucket = "open 09:31-09:59" if clock < time(10) else "morning 10:00-11:29" if clock < time(11, 30) else "midday 11:30-13:59" if clock < time(14) else "late 14:00+"
            pc, pl = bars[i - 1]["c"], vw[i - 1]
            cross = 1 if pc < pl and b["c"] > vw[i] else -1 if pc > pl and b["c"] < vw[i] else 0
            if cross:
                for name, s in (("with cross", cross), ("fade", -cross)):
                    h, r = outcome(bars, i, s, atr)
                    rows.append(dict(rule=f"VWAP {name}", bucket=bucket, day=day, hit=h, r=r))
                h, r = outcome(bars, i, 1 if e9 > e21 else -1, atr)
                rows.append(dict(rule="VWAP EMA9/21 side", bucket=bucket, day=day, hit=h, r=r))
            if clock >= time(9, 45) and hi is not None:
                out = 1 if b["c"] > hi else -1 if b["c"] < lo else 0
                if first_break is None and out:
                    first_break = (i, out)
                    h, r = outcome(bars, i, out, atr)
                    rows.append(dict(rule="ORB first break only", bucket=bucket, day=day, hit=h, r=r))
                elif first_break and not faded and not out and i - first_break[0] <= 15:
                    faded = True
                    h, r = outcome(bars, i, -first_break[1], atr)
                    rows.append(dict(rule="ORB failed break, fade back in", bucket=bucket, day=day, hit=h, r=r))
            prev = b["c"]


def fmt(name, part):
    if not part:
        return f"{name:<46} n=0"
    def mean(k):
        x = [p["r"][k] for p in part if k in p["r"]]
        return st.mean(x) if x else float("nan")
    d = defaultdict(list)
    for p in part:
        if "r30" in p["r"]:
            d[p["day"]].append(p["r"]["r30"])
    dm = [st.mean(x) for x in d.values()]
    dayt = st.mean(dm) / (st.stdev(dm) / math.sqrt(len(dm))) if len(dm) > 2 and st.stdev(dm) else float("nan")
    return f"{name:<46} n={len(part):<5} days={len(d):<3} target%={sum(p['hit'] == 'TARGET' for p in part) / len(part) * 100:5.1f} r15={mean('r15'):+.2f} r30={mean('r30'):+.2f} rEnd={mean('end'):+.2f} dayT={dayt:+.2f}"


L.append(f"== 2. Rules as designed, true session VWAP, stock only. {len(days)} days. Early before {half}.")
for rule in sorted({p["rule"] for p in rows}):
    part = [p for p in rows if p["rule"] == rule]
    L.append(fmt(rule, part))
    L.append(fmt("   early", [p for p in part if p["day"] < half]))
    L.append(fmt("   late", [p for p in part if p["day"] >= half]))
    for b in ("open 09:31-09:59", "morning 10:00-11:29", "midday 11:30-13:59", "late 14:00+"):
        L.append(fmt("   " + b, [p for p in part if p["bucket"] == b]))
open("reports/edge-hunt-2026-11-06/third_pass.txt", "w").write("\n".join(L) + "\n")
print("\n".join(L))
