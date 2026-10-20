"""Range bots: every trade with the conditions at entry, and P&L grouped by each condition.

Reads logs/*-live.jsonl (events) and data/webull/DAY/stock-T.json (Webull 1m bars, for the opening range
and the rest-of-day move). Writes range_trades_features.csv and criteria.txt in this folder.

Conditions per trade:
  window       minutes after the 7:30 MDT open (0-30, 30-60, 60-90, 90-120, 120+)
  nth          1st, 2nd, 3rd... range trade of that bot that day
  break_dir    which way price closed out of the 9:30-9:44 ET range (up/down)
  side_agrees  traded side matches the break (trend_side=True can trade a break up as a PUT)
  vwap_side    price on the traded side of VWAP at entry (above for CALL, below for PUT)
  range_atr    opening-range height / ATR at entry (terciles)
  open_drive   9:30->9:45 ET move in the traded direction (with / against)
  day_with     hindsight: price at 15:55 ET is further in the traded direction than the entry price
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from scalpcity.history import read_day, read_webull_bars  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
LOGS, WB = os.path.join(ROOT, "logs"), os.path.join(ROOT, "data", "webull")
MT, ET = ZoneInfo("America/Denver"), ZoneInfo("America/New_York")
days = sorted({m.group(1) for n in os.listdir(LOGS) if (m := re.match(r"^(\d{4}-\d{2}-\d{2})-live\.jsonl$", n))})

rows = []
for day in days:
    bars = {}
    for tk in ("SPY", "QQQ", "IWM"):
        bars[tk] = read_webull_bars(WB, tk, day) or []
    nth = defaultdict(int)
    cur = {}
    for e in read_day(LOGS, day, "live") or []:
        bot = e.get("bot") or ""
        if "RANGE" not in bot:
            continue
        kind, code, inp = e.get("kind"), e.get("reason_code"), e.get("inputs") or {}
        if kind == "state_change" and code == "SIGNAL":
            m = re.search(r"\b(CALL|PUT)\b", e.get("reason_text") or "")
            cur[bot] = {"side": m.group(1) if m else None, "sig_time": e["time"], "price": inp.get("price"),
                        "vwap": inp.get("vwap"), "atr": inp.get("atr"), "ema9": inp.get("ema9"), "ema21": inp.get("ema21")}
        elif kind == "fill" and code == "ENTRY_FILL" and bot in cur:
            cur[bot]["entry_time"] = e["time"]
        elif kind == "trade_closed" and bot in cur and "entry_time" in cur[bot]:
            c = cur.pop(bot)
            tk = bot.split("-")[0]
            nth[bot] += 1
            b = bars[tk]
            rng = [x for x in b if x.ts.time() >= datetime.strptime("09:30", "%H:%M").time() and x.ts.time() < datetime.strptime("09:45", "%H:%M").time()]
            hi = max(x.high for x in rng) if rng else None
            lo = min(x.low for x in rng) if rng else None
            p, sgn = c["price"], (1 if c["side"] == "CALL" else -1)
            brk = None if hi is None else ("up" if p > hi else "down" if p < lo else "inside")
            agrees = None if brk in (None, "inside") else ((brk == "up") == (c["side"] == "CALL"))
            drive = (rng[-1].close - rng[0].open) if rng else None
            late = [x for x in b if x.ts.time() <= datetime.strptime("15:55", "%H:%M").time()]
            day_move = (late[-1].close - p) * sgn if late and p else None
            et = datetime.fromisoformat(c["entry_time"]).astimezone(MT)
            mins = (et.hour * 60 + et.minute) - (7 * 60 + 30)
            held = (datetime.fromisoformat(e["time"]) - datetime.fromisoformat(c["entry_time"])).total_seconds() / 60
            rows.append({
                "day": day, "bot": bot, "side": c["side"], "entry_mt": et.strftime("%H:%M"), "min_after_open": mins,
                "window": "0-30" if mins < 30 else "30-60" if mins < 60 else "60-90" if mins < 90 else "90-120" if mins < 120 else "120+",
                "nth": nth[bot], "break_dir": brk, "side_agrees": agrees,
                "vwap_side": None if c["vwap"] is None else ((p - c["vwap"]) * sgn > 0),
                "range_atr": round((hi - lo) / c["atr"], 2) if hi is not None and c["atr"] else None,
                "open_drive": None if drive is None else ("with" if drive * sgn > 0 else "against"),
                "day_with": None if day_move is None else day_move > 0,
                "held_min": round(held, 1), "pnl": round(e["pnl"], 2),
            })

with open(os.path.join(OUT, "range_trades_features.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

ra = sorted(r["range_atr"] for r in rows if r["range_atr"] is not None)
t1, t2 = ra[len(ra) // 3], ra[2 * len(ra) // 3]
for r in rows:
    v = r["range_atr"]
    r["range_atr_band"] = None if v is None else (f"<{t1}" if v < t1 else f"{t1}-{t2}" if v < t2 else f">={t2}")
    r["nth_band"] = str(r["nth"]) if r["nth"] < 3 else "3+"

lines = [f"days: {days}", f"range trades: {len(rows)}  total pnl: {round(sum(r['pnl'] for r in rows), 2)}", ""]
for key in ("window", "nth_band", "side", "break_dir", "side_agrees", "vwap_side", "range_atr_band", "open_drive", "day_with", "bot"):
    g = defaultdict(list)
    for r in rows:
        g[str(r[key])].append(r)
    lines.append(f"== {key}")
    lines.append(f"  {'value':12s} {'n':>3s} {'pnl':>8s} {'avg':>7s} {'win%':>5s} {'days+':>5s} {'days-':>5s}")
    for k in sorted(g):
        xs = g[k]; n = len(xs); p = sum(x["pnl"] for x in xs)
        per = defaultdict(float)
        for x in xs:
            per[x["day"]] += x["pnl"]
        lines.append(f"  {k:12s} {n:3d} {p:8.0f} {p / n:7.0f} {100 * sum(x['pnl'] > 0 for x in xs) / n:5.0f} "
                     f"{sum(v > 0 for v in per.values()):5d} {sum(v < 0 for v in per.values()):5d}")
    lines.append("")
open(os.path.join(OUT, "criteria.txt"), "w").write("\n".join(lines))
print("\n".join(lines))
