"""Per-bot and per-strategy P&L over the logged paper days, read from logs/*-live.jsonl trade_closed events.
Also measures how far each RANGE entry closed past the opening-range edge. Run from the repo root."""
import glob, json, os
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
# Left out at the user's request (2026-10-14): today's two winning RANGE trades, judged a fluke.
EXCLUDE = {("2026-10-14", "QQQ-RANGE", "09:48"), ("2026-10-14", "SPY-RANGE", "09:50")}
rows, excluded = [], []
for path in sorted(glob.glob("logs/*-live.jsonl")):
    day = os.path.basename(path)[:10]
    ev = [json.loads(l) for l in open(path)]
    sig = {}
    for e in ev:
        if e.get("kind") == "state_change" and e.get("reason_code") == "SIGNAL":
            sig[e["bot"]] = e
        if e.get("kind") == "trade_closed":
            s = sig.get(e["bot"], {})
            dest = excluded if (day, e["bot"], s.get("time", "")[11:16]) in EXCLUDE else rows
            dest.append({"day": day, "bot": e["bot"], "strategy": e["bot"].split("-")[1], "ticker": e["ticker"],
                         "entry_time": s.get("time", "")[11:16], "exit_time": e["time"][11:16],
                         "signal": s.get("reason_text", ""), "pnl": e.get("pnl") or 0.0, "inputs": s.get("inputs", {})})

lines = []
def p(*a): lines.append(" ".join(str(x) for x in a))

days = sorted({r["day"] for r in rows})
p("Logged paper days:", ", ".join(days), "(the newest day may be still in progress)")
for r in excluded:
    p(f"Excluded: {r['day']} {r['bot']} {r['entry_time']} {r['signal']} pnl {r['pnl']:+.0f}")
p()
p("== By strategy and day (P&L $, trades, wins)")
agg = defaultdict(lambda: [0.0, 0, 0])
for r in rows:
    for k in ((r["strategy"], r["day"]), (r["strategy"], "ALL")):
        a = agg[k]; a[0] += r["pnl"]; a[1] += 1; a[2] += r["pnl"] > 0
for strat in ("VWAP", "EMA50", "RANGE"):
    cells = []
    for d in days + ["ALL"]:
        a = agg[(strat, d)]
        cells.append(f"{d}: {a[0]:+.0f} ({a[1]}t {a[2]}w)")
    p(f"{strat:6}", " | ".join(cells))
p()
p("== By bot, all days (P&L $, trades, win rate, avg per trade)")
bot = defaultdict(lambda: [0.0, 0, 0])
for r in rows:
    a = bot[r["bot"]]; a[0] += r["pnl"]; a[1] += 1; a[2] += r["pnl"] > 0
for b, a in sorted(bot.items(), key=lambda kv: kv[1][0]):
    p(f"{b:10} {a[0]:+8.0f}  {a[1]:3d} trades  {100*a[2]/a[1]:5.1f}% wins  {a[0]/a[1]:+7.1f}/trade")
p()
p("== RANGE entries: how far the signal close was past the opening-range edge")
p("(edge = signal price minus EMA-free range edge is not logged directly; distance shown in cents and in ATR using the signal's ATR)")

from datetime import datetime, timedelta

def bars(day, ticker):
    full = f"data/webull/{day}/stock-{ticker}.json"
    if os.path.exists(full):
        out = []
        for b in json.load(open(full)):
            t = datetime.fromisoformat(b["time"].replace(".000+0000", "+00:00")) - timedelta(hours=4)
            out.append((t.strftime("%H:%M"), float(b["high"]), float(b["low"])))
        return out
    live = f"data/webull/{day}/stock-{ticker}.live.jsonl"
    if os.path.exists(live):
        return [(json.loads(l)["time"][11:16], json.loads(l)["high"], json.loads(l)["low"]) for l in open(live)]
    return []

lines.pop()  # replace the placeholder note above
p("(opening range = high/low of the 9:30-9:44 Webull bars; margin = how far the signal close went past that edge)")
small = [0, 0.0]
flip = [0, 0.0]
for r in rows:
    if r["strategy"] != "RANGE":
        continue
    orb = [b for b in bars(r["day"], r["ticker"]) if "09:30" <= b[0] <= "09:44"]
    price, atr = r["inputs"].get("price"), r["inputs"].get("atr")
    if not orb or price is None:
        p(r["day"], r["bot"], r["entry_time"], "no Webull bars for the range"); continue
    hi, lo = max(b[1] for b in orb), min(b[2] for b in orb)
    side = "CALL" if "CALL" in r["signal"] else "PUT"
    brk = "UP" if price > hi else "DOWN"             # which edge the close went through
    margin = price - hi if brk == "UP" else lo - price
    flipped = (brk == "UP") != (side == "CALL")       # trend_side traded against the breakout
    tag = ""
    if margin < 0.05:
        small[0] += 1; small[1] += r["pnl"]; tag += "  <5c"
    if flipped:
        flip[0] += 1; flip[1] += r["pnl"]; tag += "  FLIPPED"
    p(f"{r['day']} {r['bot']:9} {r['entry_time']} broke {brk:4} traded {side:4} range {lo:.2f}-{hi:.2f} close {price:.3f} "
      f"margin {100*margin:5.1f}c ({margin/atr if atr else 0:4.2f} ATR)  pnl {r['pnl']:+.0f}{tag}")
p()
p(f"RANGE entries that broke out by less than 5 cents: {small[0]}, total P&L {small[1]:+.0f}")
p(f"RANGE entries traded against the breakout direction (trend_side flip): {flip[0]}, total P&L {flip[1]:+.0f}")
both = [0, 0.0]

open(os.path.join(OUT, "scorecard.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
