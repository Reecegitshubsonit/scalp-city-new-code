"""Second pass. Run from the repo root.
1. Is the logged VWAP the true session VWAP? Compares against VWAP rebuilt from recorded RTH Webull bars (same formula as SessionVwap).
2. Why is option P&L worse in the late half when the target rate is flat? Actual exits, wins, losses, stop overshoot.
3. Is the 1 ATR stop sized for the volatility that follows? ATR at signal against mean true range of the next 15 bars.
"""
import glob
import json
import os
import statistics as st
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
days = sorted(os.path.basename(f)[:10] for f in glob.glob("logs/*-live.jsonl") if "2026-11-06" not in f)
half = days[len(days) // 2]
L = []


def bars_of(day, t):
    p = f"data/webull/{day}/stock-{t}.json"
    if not os.path.exists(p):
        return {}
    out, pv, v = {}, 0.0, 0.0
    prev = None
    for b in json.load(open(p)):
        ts = datetime.fromisoformat(b["time"].replace("+0000", "+00:00")).astimezone(NY)
        if not time(9, 30) <= ts.time() < time(16):
            continue
        h, l, c, vol = float(b["high"]), float(b["low"]), float(b["close"]), float(b["volume"])
        pv += (h + l + c) / 3 * vol
        v += vol
        tr = h - l if prev is None else max(h - l, abs(h - prev), abs(l - prev))
        prev = c
        out[ts + timedelta(minutes=1)] = dict(close=c, vwap=pv / v, tr=tr, h=h, l=l)
    return out


first_rows, sig_rows, trades = [], [], []
ratio = defaultdict(list)
for day in days:
    B = {t: bars_of(day, t) for t in ("QQQ", "SPY", "IWM")}
    seen, sig = set(), {}
    for line in open(f"logs/{day}-live.jsonl"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        bot = e.get("bot") or ""
        inp = e.get("inputs") or {}
        when = datetime.fromisoformat(e["time"]) if e.get("time") else None
        t = bot.split("-")[0]
        if bot.endswith("-VWAP") and inp.get("vwap") and when in B.get(t, {}) and t not in seen and e.get("kind") in ("tick", "state_change"):
            seen.add(t)
            true = B[t][when]["vwap"]
            first_rows.append((day, t, when.time(), inp["vwap"], round(true, 3), round((inp["vwap"] - true) / (inp.get("atr") or 1), 2)))
        if e.get("kind") == "state_change" and e.get("reason_code") == "SIGNAL":
            sig[bot] = dict(price=inp["price"], atr=inp["atr"], side=e["reason_text"].split()[0], when=when)
            if when in B.get(t, {}):
                keys = sorted(k for k in B[t] if when < k <= when + timedelta(minutes=15))
                if keys and inp.get("atr"):
                    bucket = "09:30-09:44" if when.time() < time(9, 45) else "09:45-09:59" if when.time() < time(10) else "10:00-11:29" if when.time() < time(11, 30) else "11:30-13:59" if when.time() < time(14) else "14:00+"
                    ratio[bucket].append(st.mean(B[t][k]["tr"] for k in keys) / inp["atr"])
            if bot.endswith("-VWAP") and when in B.get(t, {}) and inp.get("vwap"):
                true = B[t][when]["vwap"]
                prevk = when - timedelta(minutes=1)
                pv = B[t].get(prevk)
                real = bool(pv and ((pv["close"] < pv["vwap"] and inp["price"] > true) or (pv["close"] > pv["vwap"] and inp["price"] < true)))
                sig_rows.append(dict(day=day, bot=bot, logged=inp["vwap"], true=true, price=inp["price"], atr=inp["atr"], real=real))
        if e.get("kind") == "state_change" and (e.get("reason_code") or "").startswith("EXIT_") and e["reason_code"] != "EXIT_RETRY" and bot in sig:
            sig[bot]["exit"] = e["reason_code"][5:]
        if e.get("kind") == "trade_closed" and bot in sig:
            s = sig[bot]
            sgn = 1 if s["side"] == "CALL" else -1
            trades.append(dict(day=day, bot=bot, pnl=e["pnl"], exit=s.get("exit", "?"), move=sgn * (inp.get("price", s["price"]) - s["price"]) / s["atr"], atr=s["atr"],
                               mins=(when - s["when"]).total_seconds() / 60))

L.append("== 1. Logged VWAP vs true session VWAP, first logged value of each day")
bad = [r for r in first_rows if abs(r[5]) > 0.5]
L.append(f"ticker-days checked {len(first_rows)}, off by more than 0.5 ATR: {len(bad)}, on days: {sorted({r[0] for r in bad})}")
for r in first_rows:
    L.append("  " + "  ".join(str(x) for x in r))
L.append("")
L.append("== VWAP signals against rebuilt VWAP")
n = len(sig_rows)
off = [s for s in sig_rows if abs(s["logged"] - s["true"]) / s["atr"] > 0.25]
wrong_side = [s for s in sig_rows if (s["price"] > s["logged"]) != (s["price"] > s["true"])]
L.append(f"signals {n}; logged differs by >0.25 ATR: {len(off)}; price on wrong side of true VWAP: {len(wrong_side)}; true cross on that bar: {sum(s['real'] for s in sig_rows)}")
L.append(f"mean |logged-true| in ATR: {st.mean(abs(s['logged'] - s['true']) / s['atr'] for s in sig_rows):.2f}")
L.append("")

L.append("== 2. Actual trades by half (early before " + half + ")")
for name, rows in (("early", [t for t in trades if t["day"] < half]), ("late", [t for t in trades if t["day"] >= half])):
    w = [t["pnl"] for t in rows if t["pnl"] > 0]
    l = [t["pnl"] for t in rows if t["pnl"] <= 0]
    ex = defaultdict(list)
    for t in rows:
        ex[t["exit"]].append(t)
    L.append(f"{name}: trades {len(rows)}, P&L {sum(t['pnl'] for t in rows):.0f}, win% {len(w) / len(rows) * 100:.1f}, avg win {st.mean(w):.0f}, avg loss {st.mean(l):.0f}, mean entry ATR {st.mean(t['atr'] for t in rows):.3f}, mean minutes {st.mean(t['mins'] for t in rows):.1f}")
    for k, v in sorted(ex.items()):
        L.append(f"   {k}: {len(v)} ({len(v) / len(rows) * 100:.1f}%), mean P&L {st.mean(t['pnl'] for t in v):.0f}, mean stock move {st.mean(t['move'] for t in v):+.2f} ATR, worst {min(t['move'] for t in v):+.2f}, best {max(t['move'] for t in v):+.2f}, mean minutes {st.mean(t['mins'] for t in v):.1f}")
L.append("")

L.append("== 3. Mean true range of next 15 bars / ATR at signal (1.0 = stop sized to coming volatility)")
for k in sorted(ratio):
    v = ratio[k]
    L.append(f"{k}: signals {len(v)}, mean {st.mean(v):.2f}, median {st.median(v):.2f}")

open("reports/edge-hunt-2026-11-06/second_pass.txt", "w").write("\n".join(L) + "\n")
print("\n".join(L))
