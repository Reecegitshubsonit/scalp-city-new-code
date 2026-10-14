"""Fake simulation: replay the finished paper days through the engine twice, all data from Webull
(data/webull/DAY/), and compare the RANGE bots with the live rule (any close past the opening range)
against a 5-cent rule (the close must be at least $0.05 past the range edge). Every other bot and
setting is identical in both runs. Run from the repo root: .venv/bin/python reports/range-5c-sim-2026-10-14/sim.py"""
import json
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.getcwd())
from scalpcity import engine as engine_mod
from scalpcity.broker import ModeledBroker
from scalpcity.config import TICKERS, Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.quotes import BarQuoteSource
from scalpcity.replay import ReplayFeed, run_replay
from scalpcity.triggers import RangeBreak, TriggerView, charge
from scalpcity.types import Bar
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = "data/webull"
DAYS = [date(2026, 10, 9), date(2026, 10, 12), date(2026, 10, 13)]   # finished paper days with Webull full-day files
MARGIN = 0.05


def wb_time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace(".000+0000", "+00:00").replace("Z", "+00:00")).astimezone(ET)


def stock_bars(ticker: str, day: date) -> list[Bar]:
    path = f"{ROOT}/{day}/stock-{ticker}.json"
    if not os.path.exists(path):
        return []
    return [Bar(ticker, wb_time(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]),
                float(r["volume"])) for r in json.load(open(path))]


MISSING: dict = {}


def option_closes(contract: str, ts: datetime):
    day = ts.astimezone(ET).date()
    path = f"{ROOT}/{day}/option-{contract}.json"
    if not os.path.exists(path):
        MISSING.setdefault((str(day), contract), ts.strftime("%H:%M"))
        return []
    return [(wb_time(r["time"]), float(r["close"])) for r in json.load(open(path))]


class RangeBreakMargin(RangeBreak):
    """Same as RangeBreak, but a breakout needs the close to be at least `margin` dollars past the range edge.
    A close past the edge by less than the margin still counts as inside, so a later bar can still fire."""
    margin = MARGIN

    def update(self, bar, ind):
        t = bar.ts.time()
        if self.start <= t < self.end or self.hi is None:
            return super().update(bar, ind)
        hi, lo = self.hi + self.margin, self.lo - self.margin
        atr = ind.atr.value or 0.0
        inside = lo <= bar.close <= hi
        prev_inside = self.prev_close is not None and lo <= self.prev_close <= hi
        sig = None
        if prev_inside and bar.close > hi:
            sig = "CALL"
        elif prev_inside and bar.close < lo:
            sig = "PUT"
        self.prev_close = bar.close
        if inside:
            dist = min(hi - bar.close, bar.close - lo) / atr if atr > 0 else 0.0
            pct = charge(dist, self.rng)
        else:
            dist, pct = 0.0, (100.0 if sig else 0.0)
        return TriggerView(signal=sig, charge_pct=pct, distance_atr=round(dist, 3))


def run(label: str, range_cls) -> dict:
    engine_mod._TRIGGERS["range"] = range_cls
    settings = Settings(daily_loss=800.0)          # same per-bot loss limit the live engine runs with
    bars = {t: [b for d in DAYS for b in stock_bars(t, d)] for t in TICKERS}
    feed = ReplayFeed(bars)
    out = {}
    for day in DAYS:
        log = EventLog(os.path.join(OUT, "logs", label), "sim")
        quotes = BarQuoteSource(option_closes, settings.half_spread)
        eng = Engine(settings, log, ModeledBroker(), quotes)
        run_replay(eng, feed, day)
        trades = []
        sig = {}
        for e in log.read(day):
            if e.get("kind") == "state_change" and e.get("reason_code") == "SIGNAL":
                sig[e["bot"]] = e
            if e.get("kind") == "trade_closed":
                s = sig.get(e["bot"], {})
                trades.append({"bot": e["bot"], "entry": s.get("time", "")[11:16], "exit": e["time"][11:16],
                               "signal": s.get("reason_text", ""), "pnl": e.get("pnl") or 0.0})
        out[str(day)] = trades
    return out


base = run("live-rule", RangeBreak)
miss_base = dict(MISSING); MISSING.clear()
five = run("5-cent-rule", RangeBreakMargin)
miss_five = dict(MISSING)

lines = []
p = lambda *a: lines.append(" ".join(str(x) for x in a))
p("RANGE bots: live rule (any close past the opening range) vs 5-cent rule (close >= $0.05 past the edge)")
p("Days:", ", ".join(str(d) for d in DAYS), "| data: Webull bars and Webull option bars only | fills: modeled (bar close +/- half spread)")
p("Today's day (2026-10-14) is left out: it is still trading and its option bars are not saved yet.")
p("Oct 9 starts with no warm-up bars (no Webull day before it), so its EMAs start cold.")
p()
tot = {"live-rule": [0.0, 0, 0], "5-cent-rule": [0.0, 0, 0]}
for day in map(str, DAYS):
    p(f"== {day}")
    for label, res in (("live-rule", base), ("5-cent-rule", five)):
        rt = [t for t in res[day] if "RANGE" in t["bot"]]
        pnl = sum(t["pnl"] for t in rt); w = sum(t["pnl"] > 0 for t in rt)
        tot[label][0] += pnl; tot[label][1] += len(rt); tot[label][2] += w
        p(f"  {label:12} RANGE {pnl:+8.0f}  {len(rt):2d} trades  {w:2d} wins")
        for t in rt:
            p(f"      {t['bot']:9} {t['entry']}-{t['exit']} {t['signal']:28} {t['pnl']:+7.0f}")
p()
p("== Total RANGE over the days")
for label, (pnl, n, w) in tot.items():
    p(f"  {label:12} {pnl:+8.0f}  {n} trades  {w} wins")
p()
p("== By RANGE bot, total")
for b in [f"{t}-RANGE" for t in TICKERS]:
    a = sum(t["pnl"] for d in base.values() for t in d if t["bot"] == b)
    c = sum(t["pnl"] for d in five.values() for t in d if t["bot"] == b)
    p(f"  {b:10} live-rule {a:+7.0f}   5-cent-rule {c:+7.0f}   change {c - a:+7.0f}")
p()
p("== Option contracts the run wanted but Webull has no saved bars for (entry or exit could not be priced)")
for label, m in (("live-rule", miss_base), ("5-cent-rule", miss_five)):
    p(f"  {label}: " + (", ".join(f"{d} {c} first asked {t}" for (d, c), t in sorted(m.items())) or "none"))
p()
p("== Sanity check: live-rule replay vs what actually happened (RANGE P&L per day, real fills)")
for day in map(str, DAYS):
    real = sum(json.loads(l).get("pnl") or 0.0 for l in open(f"logs/{day}-live.jsonl")
               if '"trade_closed"' in l and "RANGE" in l)
    sim = sum(t["pnl"] for t in base[day] if "RANGE" in t["bot"])
    p(f"  {day}  real {real:+7.0f}   replay {sim:+7.0f}")

open(os.path.join(OUT, "results.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
