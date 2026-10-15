"""Volume at entry vs trade outcome, on the Webull paper days. Run from repo root.

For every closed trade in logs/DAY-live.jsonl, look up the 1-minute Webull bar the bot signalled on
(data/webull/DAY/stock-T.json, or stock-T.live.jsonl when the end-of-day file is not written yet) and measure:
  rel1   signal-bar volume / average volume of the 20 bars before it (same session only)
  rel3   average volume of the signal bar and the 2 before it / average of the 20 bars before those
  dir5   same as flow5 without the volume weights (fraction of the last 5 bars moving the trade's way, net)
  move5  price move over the last 5 bars, turned to the trade's side (positive = already moved the trade's way)
  flow5  volume-weighted direction of the last 5 bars (signal bar included), sign(close-open) * volume / volume,
         turned to the trade's side: +1 = all volume on bars moving the trade's way, -1 = all against it
  agree  signal bar itself moved the trade's way (PUT on a red bar, CALL on a green bar)
Bar volume is total shares, buyers plus sellers; candle direction is only a proxy for who pushed.
Trades signalled with fewer than 10 bars of session behind them are reported apart ("early"), because the
opening bars carry volume no later bar can match and would skew every ratio.
"""
import json, os, statistics as st, collections
from datetime import datetime, timedelta, timezone

DAYS = ["2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"]
MIN_PRIOR = 10


def load_bars(day, t):
    d = f"data/webull/{day}"
    if os.path.exists(f"{d}/stock-{t}.json"):
        rows = json.load(open(f"{d}/stock-{t}.json"))
        out = []
        for r in rows:
            ts = datetime.strptime(r["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            out.append((ts, float(r["open"]), float(r["close"]), float(r["volume"])))
        return out, "eod"
    out = []
    for l in open(f"{d}/stock-{t}.live.jsonl"):
        r = json.loads(l)
        out.append((datetime.fromisoformat(r["time"]).astimezone(timezone.utc), r["open"], r["close"], r["volume"]))
    return sorted(set(out)), "live"


def trades(day):
    sig, entry, out = {}, {}, []
    for l in open(f"logs/{day}-live.jsonl"):
        e = json.loads(l)
        if e["kind"] == "state_change" and e["reason_code"] == "SIGNAL":
            sig[e["bot"]] = e
        elif e["kind"] == "fill" and e["reason_code"] == "ENTRY_FILL":
            entry[e["bot"]] = (sig.get(e["bot"]), e)
        elif e["kind"] == "trade_closed" and e["bot"] in entry:
            s, en = entry.pop(e["bot"])
            if s is None:
                continue
            side = "PUT" if "PUT" in s["reason_text"] else "CALL" if "CALL" in s["reason_text"] else None
            px = float(s["reason_text"].rsplit(" ", 1)[-1]) if " at " in s["reason_text"] else None
            out.append(dict(day=day, bot=e["bot"], ticker=e["ticker"], strat=e["bot"].split("-", 1)[1], side=side,
                            # events carry the bar's end time; the signal bar is the one that started a minute earlier
                            sig_time=datetime.fromisoformat(s["time"]).astimezone(timezone.utc) - timedelta(minutes=1), sig_px=px, pnl=e["pnl"],
                            exit=e.get("reason_code")))
    return out


rows, align, sources = [], collections.Counter(), {}
for day in DAYS:
    bars = {}
    for t in ("QQQ", "SPY", "IWM"):
        bars[t], sources[(day, t)] = load_bars(day, t)
    for tr in trades(day):
        b = bars[tr["ticker"]]
        idx = {x[0]: i for i, x in enumerate(b)}
        i = idx.get(tr["sig_time"])
        if i is None:
            align["no bar"] += 1
            continue
        # session = bars of the same ET date at or after 13:30 UTC (09:30 ET in EDT)
        first = next(k for k, x in enumerate(b) if x[0].date() == tr["sig_time"].date() and (x[0].hour, x[0].minute) >= (13, 30))
        prior = i - first
        align["close matches signal price" if tr["sig_px"] is not None and abs(b[i][2] - tr["sig_px"]) < 0.015 else "close differs"] += 1
        sgn = 1 if tr["side"] == "CALL" else -1
        d = lambda x: (x[2] > x[1]) - (x[2] < x[1])
        p20 = [x[3] for x in b[max(first, i - 20):i]]
        p20b = [x[3] for x in b[max(first, i - 22):i - 2]] if i - 2 > first else []
        last5 = b[max(first, i - 4):i + 1]
        vol5 = sum(x[3] for x in last5)
        rows.append(dict(tr, prior=prior,
                         rel1=b[i][3] / st.mean(p20) if p20 else None,
                         rel3=st.mean(x[3] for x in b[i - 2:i + 1]) / st.mean(p20b) if p20b else None,
                         flow5=sgn * sum(d(x) * x[3] for x in last5) / vol5 if vol5 else None,
                         dir5=sgn * sum(d(x) for x in last5) / len(last5),
                         move5=sgn * (b[i][2] - last5[0][1]),
                         agree=d(b[i]) * sgn > 0))

out = []
P = out.append
P("Volume at entry vs trade outcome, Webull paper days " + ", ".join(DAYS))
P("Bar source per day: " + ", ".join(f"{d} {sources[(d, 'QQQ')]}" for d in DAYS))
P(f"Trades matched to their signal bar: {len(rows)}; alignment check: {dict(align)}")
P("")


def summary(name, rs):
    if not rs:
        return
    w = [r for r in rs if r["pnl"] > 0]
    l = [r for r in rs if r["pnl"] <= 0]
    med = lambda xs, k: st.median([x[k] for x in xs if x[k] is not None]) if [x for x in xs if x[k] is not None] else float("nan")
    P(f"{name}: {len(rs)} trades, {len(w)} wins, net {sum(r['pnl'] for r in rs):+.0f}")
    P(f"   median rel1   winners {med(w, 'rel1'):.2f}  losers {med(l, 'rel1'):.2f}")
    P(f"   median rel3   winners {med(w, 'rel3'):.2f}  losers {med(l, 'rel3'):.2f}")
    P(f"   median flow5  winners {med(w, 'flow5'):+.2f}  losers {med(l, 'flow5'):+.2f}")
    P(f"   signal bar agrees with side: winners {sum(r['agree'] for r in w)}/{len(w)}  losers {sum(r['agree'] for r in l)}/{len(l)}")


def buckets(name, rs, key, edges, fmt):
    P(f"{name} buckets ({key}):")
    for lo, hi in edges:
        b = [r for r in rs if r[key] is not None and lo <= r[key] < hi]
        if b:
            P(f"   {fmt(lo, hi):>14}: {len(b):3} trades, {sum(r['pnl'] > 0 for r in b):3} wins ({100 * sum(r['pnl'] > 0 for r in b) / len(b):3.0f}%), net {sum(r['pnl'] for r in b):+7.0f}, avg {sum(r['pnl'] for r in b) / len(b):+5.0f}")


main = [r for r in rows if r["prior"] >= MIN_PRIOR]
early = [r for r in rows if r["prior"] < MIN_PRIOR]
summary("ALL (10+ bars into session)", main)
summary("EARLY (first 10 bars)", early)
P("")
for s in ("VWAP", "EMA50", "RANGE"):
    summary(s, [r for r in main if r["strat"] == s])
P("")
buckets("ALL", main, "rel1", [(0, 0.8), (0.8, 1.2), (1.2, 2), (2, 99)], lambda a, b: f"{a}-{b}x" if b < 99 else f">={a}x")
buckets("ALL", main, "flow5", [(-1.01, -0.3), (-0.3, 0.3), (0.3, 1.01)], lambda a, b: "against" if b <= -0.3 else "mixed" if b <= 0.3 else "with trade")
for s in ("VWAP", "EMA50", "RANGE"):
    buckets(s, [r for r in main if r["strat"] == s], "flow5", [(-1.01, -0.3), (-0.3, 0.3), (0.3, 1.01)], lambda a, b: "against" if b <= -0.3 else "mixed" if b <= 0.3 else "with trade")
FLOW = [(-1.01, -0.3), (-0.3, 0.3), (0.3, 1.01)]
flab = lambda a, b: "against" if b <= -0.3 else "mixed" if b <= 0.3 else "with trade"
P("")
P("Control: same buckets on dir5 (no volume). If the split matches flow5, the effect is price direction, not volume.")
buckets("ALL", main, "dir5", FLOW, flab)
P("")
P("Independence: several bots often signal on the same ticker and bar. Distinct signal bars per flow5 bucket:")
for lo, hi in FLOW:
    b = [r for r in main if r["flow5"] is not None and lo <= r["flow5"] < hi]
    P(f"   {flab(lo, hi):>10}: {len(b)} trades on {len({(r['ticker'], r['sig_time']) for r in b})} distinct bars, over {len({r['day'] for r in b})} days")
P("")
P("flow5 buckets per day (is it one day carrying the result?):")
for day in DAYS:
    buckets(day, [r for r in main if r["day"] == day], "flow5", FLOW, flab)
P("")
P("Outliers: each flow5 bucket with its 3 biggest winners removed:")
for lo, hi in FLOW:
    b = sorted([r for r in main if r["flow5"] is not None and lo <= r["flow5"] < hi], key=lambda r: r["pnl"])
    rest = b[:-3]
    P(f"   {flab(lo, hi):>10}: {len(rest)} trades, {sum(r['pnl'] > 0 for r in rest)} wins, net {sum(r['pnl'] for r in rest):+.0f} (removed {[r['pnl'] for r in b[-3:]]})")
P("")
P("Every trade (ET signal time, bot, side, rel1, rel3, flow5, agree, pnl):")
for r in sorted(rows, key=lambda r: r["sig_time"]):
    et = r["sig_time"].astimezone().strftime("%H:%M")
    f = lambda v, s="": "  -  " if v is None else format(v, s or ".2f")
    P(f"  {r['day']} {(r['sig_time'].hour - 4):02d}:{r['sig_time'].minute:02d} {r['bot']:10} {r['side'] or '?':4} rel1 {f(r['rel1'])} rel3 {f(r['rel3'])} flow5 {f(r['flow5'], '+.2f')} {'agree' if r['agree'] else 'against':7} {r['pnl']:+6.0f}{'  early' if r['prior'] < MIN_PRIOR else ''}")
text = "\n".join(out)
open("reports/volume-vs-outcome-2026-10-15/output.txt", "w").write(text + "\n")
print(text)
