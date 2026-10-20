"""Range bots that turn into trend bots after their first range-break signal, on the Webull paper days.

Each range bot (IWM/QQQ/SPY-RANGE) trades the normal opening-range break once. After that first signal the
trigger switches to a trend rule for the rest of the day. Everything else is the live engine unchanged:
1 ATR stop, 2 ATR target, 2 min cooldown, side from EMA9 vs EMA21, $600 daily goal, $800 daily loss,
no entries after 15:30 ET, flat by 15:55 ET.

Variants (trend rule after the first range signal):
  range     baseline, the current range bot (needs price back inside the range for another signal)
  pullback  EMA9 trend; signal when a bar's wick reaches EMA9 and the bar closes back on the trend side
  reenter   signal on every bar in the EMA9/EMA21 direction, so the bot re-enters as soon as cooldown ends
  cross     signal when EMA9 crosses EMA21

Pricing: 10-14 onward use the recorded Webull bid/ask snapshots (buy at ask, sell at bid). 10-12 and 10-13 have
no snapshots, so they are priced from Webull option candle closes +/- the engine's half-spread, and only for the
few strikes that were saved those days; trades on other strikes are listed as unpriced. Lower fidelity.
On snapshot days a contract missing from the recorded ladder (price moved away from that strike) falls back to
candles too; those contracts are listed under "candle fallback".

Usage: .venv/bin/python reports/range-then-trend-2026-10-20/sim.py
Writes results.txt, trades.csv and per-variant/day event logs in this folder.
"""
import csv
import glob
import json
import os
import sys
from datetime import date, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.chdir(ROOT)
from replay_webull import stock_bars, trades, wb_time  # noqa: E402
from scalpcity import engine as engine_mod  # noqa: E402
from scalpcity.broker import ModeledBroker  # noqa: E402
from scalpcity.config import TICKERS, Settings  # noqa: E402
from scalpcity.engine import Engine  # noqa: E402
from scalpcity.events import EventLog  # noqa: E402
from scalpcity.quotes import BarQuoteSource, SnapshotQuoteSource  # noqa: E402
from scalpcity.replay import ReplayFeed, run_replay  # noqa: E402
from scalpcity.triggers import RangeBreak, TriggerView  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
WB = "data/webull"
DAYS = ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-20"]
VARIANTS = ["range", "pullback", "reenter", "cross"]


def trend(ind) -> str | None:
    e9, e21 = ind.ema9.value, ind.ema21.value
    if e9 is None or e21 is None or e9 == e21:
        return None
    return "CALL" if e9 > e21 else "PUT"


def range_then(rule: str):
    class RangeThenTrend(RangeBreak):
        def new_session(self):
            super().new_session()
            self.switched = False
            self.prev_side = None

        def update(self, bar, ind):
            side = trend(ind)
            prev_side, self.prev_side = self.prev_side, side
            if not self.switched:
                view = super().update(bar, ind)
                if view.signal:
                    self.switched = True
                return view
            sig = None
            if rule == "reenter":
                sig = side
            elif rule == "cross":
                sig = side if prev_side is not None and side != prev_side else None
            elif rule == "pullback" and side is not None:
                e9 = ind.ema9.value
                if side == "CALL" and bar.low <= e9 < bar.close:
                    sig = "CALL"
                elif side == "PUT" and bar.high >= e9 > bar.close:
                    sig = "PUT"
            return TriggerView(signal=sig, charge_pct=100.0 if sig else 0.0, distance_atr=0.0)
    return RangeThenTrend


class CandleQuotes(BarQuoteSource):
    """Webull option candles saved for 10-12/10-13; missing contracts are recorded as unpriced."""

    def __init__(self, half_spread):
        self.missing = {}
        self._cache = {}
        super().__init__(self._bars, half_spread)

    def _bars(self, contract, ts):
        day = ts.date().isoformat()
        key = (day, contract)
        if key not in self._cache:
            path = f"{WB}/{day}/option-{contract}.json"
            self._cache[key] = [(wb_time(r["time"]), float(r["close"])) for r in json.load(open(path))] if os.path.exists(path) else []
        return self._cache[key]

    def get(self, contract, ts):
        q = super().get(contract, ts)
        if q is None:
            self.missing.setdefault((ts.date().isoformat(), contract), ts.strftime("%H:%M"))
        return q


class SnapThenCandles:
    """Recorded bid/ask first; if the contract is not in the snapshot ladder near that minute, Webull candles."""

    def __init__(self, half_spread):
        self.snap, self.candles = SnapshotQuoteSource(WB), CandleQuotes(half_spread)
        self.fallback = {}
        self.missing = self.candles.missing

    def get(self, contract, ts):
        q = self.snap.get(contract, ts)
        if q is None:
            q = self.candles.get(contract, ts)
            if q is not None:
                self.fallback.setdefault((ts.date().isoformat(), contract), ts.strftime("%H:%M"))
        return q


def run(variant: str, day: str):
    engine_mod._TRIGGERS["range"] = RangeBreak if variant == "range" else range_then(variant)
    recorded = sorted(d for d in os.listdir(WB) if d <= day and glob.glob(f"{WB}/{d}/stock-*"))
    bars = {t: [b for d in recorded[-3:] for b in stock_bars(WB, t, d)] for t in TICKERS}
    settings = Settings(daily_loss=800.0)
    snap = os.path.exists(f"{WB}/{day}/snapshots.jsonl")
    quotes = SnapThenCandles(settings.half_spread) if snap else CandleQuotes(settings.half_spread)
    logdir = os.path.join(OUT, "logs", variant)
    os.makedirs(logdir, exist_ok=True)
    log = EventLog(logdir, "replay")
    run_replay(Engine(settings, log, ModeledBroker(), quotes), ReplayFeed(bars), date.fromisoformat(day))
    rows = [t for t in trades(log.read(date.fromisoformat(day))) if "RANGE" in t["bot"].upper()]
    fb = sorted((c, t) for (d, c), t in getattr(quotes, "fallback", {}).items() if d == day)
    range_contracts = {t["contract"] for t in rows}
    fb = [x for x in fb if x[0] in range_contracts]
    rej = [e for e in log.read(date.fromisoformat(day)) if e.get("kind") == "order_rejected" and "RANGE" in e["bot"].upper()]
    missing = sorted({(e["contract"], e["time"][11:16]) for e in rej if "entry" in e["reason_text"]} |
                     {(e["contract"], "exit") for e in rej if "exit" in e["reason_text"]})
    last_bar = max(b.ts for v in bars.values() for b in v if b.ts.date().isoformat() == day)
    return rows, missing, ("snapshots" if snap else "candles"), last_bar, fb


def main():
    all_rows, lines = [], []
    p = lambda *a: lines.append(" ".join(str(x) for x in a))
    summary = {}
    for day in DAYS:
        for v in VARIANTS:
            rows, missing, src, last_bar, fb = run(v, day)
            seen = {}
            for t in rows:
                seen[t["bot"]] = seen.get(t["bot"], 0) + 1
                all_rows.append({"variant": v, "day": day, "pricing": src, "bot": t["bot"], "n": seen[t["bot"]],
                                 "entry_et": t["entry"], "exit_et": t.get("exit"), "contract": t["contract"],
                                 "in_px": t["in_px"], "out_px": t.get("out_px"), "pnl": t["pnl"]})
            summary[(v, day)] = (rows, missing, src, last_bar, fb)

    p("Range bots: first range-break trade, then a trend rule for the rest of the day")
    p("Webull paper days, replayed through the engine. Range bots only (IWM/QQQ/SPY-RANGE). P&L in dollars, 10 contracts.")
    p("2026-10-19 skipped: engine did not run (DNS failure). 10-12/10-13 priced from option candles (lower fidelity).")
    p()
    p(f"{'day':11} {'pricing':10} " + " ".join(f"{v:>22}" for v in VARIANTS))
    tot = {v: [0.0, 0, 0, 0] for v in VARIANTS}
    for day in DAYS:
        cells = []
        for v in VARIANTS:
            rows, missing, src, last_bar, fb = summary[(v, day)]
            closed = [t for t in rows if t["pnl"] is not None]
            pnl = sum(t["pnl"] for t in closed)
            wins = sum(t["pnl"] > 0 for t in closed)
            tot[v][0] += pnl; tot[v][1] += len(closed); tot[v][2] += wins; tot[v][3] += len(missing)
            cells.append(f"{pnl:+8.0f} ({len(closed):2d}t,{wins:2d}w)".rjust(22))
        p(f"{day:11} {summary[('range', day)][2]:10} " + " ".join(cells))
    p(f"{'TOTAL':22} " + " ".join(f"{t[0]:+8.0f} ({t[1]:2d}t,{t[2]:2d}w)".rjust(22) for t in tot.values()))
    p(f"{'per trade':22} " + " ".join(f"{(t[0] / t[1] if t[1] else 0):+8.1f}".rjust(22) for t in tot.values()))
    real = {}
    for x in csv.DictReader(open("reports/range-cutoff-2026-10-20/trades.csv")):
        real.setdefault(x["day"], []).append(float(x["pnl"]))
    p(f"{'unpriced (range bots)':22} " + " ".join(f"{t[3]:>22}" for t in tot.values()))
    p()
    p("Replay check: real live range-bot P&L those days (from reports/range-cutoff-2026-10-20/trades.csv, 10-20 morning only):")
    p("  " + "  ".join(f"{d[5:]}: {sum(real.get(d, [])):+.0f} ({len(real.get(d, []))}t)" for d in DAYS))
    p("  The 'range' column is the same bot replayed; differences are replay fidelity, not strategy.")
    p()
    p(f"2026-10-20 covers bars up to {summary[('range', '2026-10-20')][3]:%H:%M} ET only (run during the session).")
    p()
    p("Per bot totals (all days):")
    for v in VARIANTS:
        by = {}
        for r in all_rows:
            if r["variant"] == v and r["pnl"] is not None:
                b = by.setdefault(r["bot"], [0.0, 0])
                b[0] += r["pnl"]; b[1] += 1
        p(f"  {v:9} " + "  ".join(f"{b}: {x[0]:+.0f} ({x[1]}t)" for b, x in sorted(by.items())))
    p()
    p("Trades after the first range trade only (the part the trend rule adds):")
    for v in VARIANTS:
        later = [r for r in all_rows if r["variant"] == v and r["n"] > 1 and r["pnl"] is not None]
        s = sum(r["pnl"] for r in later)
        p(f"  {v:9} {len(later):3d} trades  {s:+8.0f}  per trade {(s / len(later) if later else 0):+.1f}  wins {sum(r['pnl'] > 0 for r in later)}")
    p()
    p("Unpriced range-bot orders (entry refused for no quote at HH:MM, or exit retried for no quote), by variant/day:")
    for (v, day), (_, missing, _, _, _) in summary.items():
        if missing:
            p(f"  {v:9} {day}: " + ", ".join(f"{c}@{t}" for c, t in missing))
    p()
    p("Candle fallback used for range-bot contracts on snapshot days (contract@first minute):")
    for (v, day), (_, _, _, _, fb) in summary.items():
        if fb:
            p(f"  {v:9} {day}: " + ", ".join(f"{c}@{t}" for c, t in fb))
    with open(os.path.join(OUT, "trades.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader(); w.writerows(all_rows)
    open(os.path.join(OUT, "results.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
