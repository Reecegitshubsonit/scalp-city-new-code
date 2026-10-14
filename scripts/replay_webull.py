"""Replay one paper day through the engine with Webull data only, priced from the real bid/ask the recorder saved,
and compare every replayed trade with what the live engine really did that day.

Fills: buy at the recorded ask, sell at the recorded bid (snapshots.jsonl). A trade with no recorded quote is
listed as unpriced; nothing is filled from candle closes. Only days recorded with snapshots (2026-10-14 on) work.

Usage: .venv/bin/python scripts/replay_webull.py 2026-10-14 [--range-margin 0.05] [--daily-loss 800]
Writes reports/replay-webull/DAY[-rangeM]/results.txt and the replay event log next to it.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity import engine as engine_mod
from scalpcity.broker import ModeledBroker
from scalpcity.config import TICKERS, Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.quotes import SnapshotQuoteSource
from scalpcity.replay import ReplayFeed, run_replay
from scalpcity.triggers import RangeBreak, TriggerView, charge
from scalpcity.types import ET, Bar


def wb_time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace(".000+0000", "+00:00")).astimezone(ET)


def stock_bars(root: str, ticker: str, day: str) -> list[Bar]:
    """Webull's end-of-day full-day file, else the bars the live engine received that day."""
    full, live = f"{root}/{day}/stock-{ticker}.json", f"{root}/{day}/stock-{ticker}.live.jsonl"
    rows = {}
    if os.path.exists(full):
        for r in json.load(open(full)):
            rows[wb_time(r["time"])] = r
    elif os.path.exists(live):
        for line in open(live):
            r = json.loads(line)
            if r["time"][:10] == day:
                rows[datetime.fromisoformat(r["time"])] = r
    return [Bar(ticker, t, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"]))
            for t, r in sorted(rows.items())]


def range_with_margin(margin: float):
    class RangeBreakMargin(RangeBreak):
        """RangeBreak where the close must be at least `margin` dollars past the range edge to count as a breakout."""

        def update(self, bar, ind):
            if self.start <= bar.ts.time() < self.end or self.hi is None:
                return super().update(bar, ind)
            hi, lo = self.hi + margin, self.lo - margin
            atr = ind.atr.value or 0.0
            inside = lo <= bar.close <= hi
            prev_inside = self.prev_close is not None and lo <= self.prev_close <= hi
            sig = "CALL" if prev_inside and bar.close > hi else "PUT" if prev_inside and bar.close < lo else None
            self.prev_close = bar.close
            if inside:
                dist = min(hi - bar.close, bar.close - lo) / atr if atr > 0 else 0.0
                return TriggerView(signal=sig, charge_pct=charge(dist, self.rng), distance_atr=round(dist, 3))
            return TriggerView(signal=sig, charge_pct=100.0 if sig else 0.0, distance_atr=0.0)
    return RangeBreakMargin


def trades(events: list[dict]) -> list[dict]:
    """One row per closed trade: entry/exit fill and the bid/ask it was priced from."""
    out, open_ = [], {}
    for e in events:
        if e.get("kind") == "fill" and e.get("reason_code") == "ENTRY_FILL":
            open_[e["bot"]] = {"bot": e["bot"], "entry": e["time"][11:16], "contract": e.get("contract"),
                               "in_px": e.get("fill_price"), "in_q": (e.get("quote_bid"), e.get("quote_ask"))}
        elif e.get("kind") == "fill" and e.get("reason_code") == "EXIT_FILL" and e["bot"] in open_:
            open_[e["bot"]].update(exit=e["time"][11:16], out_px=e.get("fill_price"), out_q=(e.get("quote_bid"), e.get("quote_ask")))
        elif e.get("kind") == "trade_closed" and e["bot"] in open_:
            out.append({**open_.pop(e["bot"]), "pnl": e.get("pnl") or 0.0})
    return out + [{**t, "pnl": None} for t in open_.values()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("day")
    ap.add_argument("--root", default="data/webull")
    ap.add_argument("--logdir", default="logs")
    ap.add_argument("--range-margin", type=float, default=0.0)
    ap.add_argument("--daily-loss", type=float, default=800.0, help="same per-bot loss limit the live engine runs with")
    args = ap.parse_args()
    day = date.fromisoformat(args.day)
    label = args.day + (f"-range{args.range_margin:g}" if args.range_margin else "")
    out = os.path.join("reports", "replay-webull", label)
    os.makedirs(out, exist_ok=True)

    if args.range_margin:
        engine_mod._TRIGGERS["range"] = range_with_margin(args.range_margin)
    recorded = sorted(d for d in os.listdir(args.root) if d <= args.day)
    bars = {t: [b for d in recorded[-3:] for b in stock_bars(args.root, t, d)] for t in TICKERS}   # 2 prior days warm up
    settings = Settings(daily_loss=args.daily_loss)
    quotes = SnapshotQuoteSource(args.root)
    log = EventLog(out, "replay")
    engine = Engine(settings, log, ModeledBroker(), quotes)
    run_replay(engine, ReplayFeed(bars), day)

    real_path = os.path.join(args.logdir, f"{args.day}-live.jsonl")
    real = trades([json.loads(l) for l in open(real_path)]) if os.path.exists(real_path) else []
    sim = trades(log.read(day))
    lines = []
    p = lambda *a: lines.append(" ".join(str(x) for x in a))
    p(f"Replay of {args.day}: Webull bars, fills at the recorded Webull bid/ask (buy at ask, sell at bid)")
    p(f"range margin {args.range_margin:g}, daily loss {args.daily_loss:g}, warm-up days: {', '.join(recorded[-3:-1]) or 'none'}")
    p()
    p(f"{'bot':10} {'real entry-exit':16} {'real in/out':12} {'real P&L':>8} | {'replay entry-exit':17} {'replay in/out':13} {'replay P&L':>10}")
    for b in sorted({t['bot'] for t in real + sim}):
        r = [t for t in real if t["bot"] == b]
        s = [t for t in sim if t["bot"] == b]
        for i in range(max(len(r), len(s))):
            a = r[i] if i < len(r) else None
            c = s[i] if i < len(s) else None
            left = (f"{a['entry']}-{a.get('exit', '--:--')}   {a['in_px']}/{a.get('out_px')}".ljust(29) +
                    f"{a['pnl'] if a['pnl'] is not None else 'open':>8}") if a else " " * 37
            right = (f"{c['entry']}-{c.get('exit', '--:--')}    {c['in_px']}/{c.get('out_px')}".ljust(31) +
                     f"{c['pnl'] if c['pnl'] is not None else 'open':>10}") if c else ""
            p(f"{b:10} {left} | {right}")
    rp, sp = sum(t["pnl"] or 0 for t in real), sum(t["pnl"] or 0 for t in sim)
    p()
    p(f"Total closed P&L: real {rp:+.0f} ({len(real)} trades)   replay {sp:+.0f} ({len(sim)} trades)")
    same = [(a, c) for a in real for c in sim if a["bot"] == c["bot"] and a["entry"] == c["entry"] and a["contract"] == c["contract"]]
    if same:
        gaps = [abs((c["in_px"] or 0) - (a["in_px"] or 0)) for a, c in same] + \
               [abs((c.get("out_px") or 0) - (a.get("out_px") or 0)) for a, c in same if a.get("out_px") and c.get("out_px")]
        p(f"Same trade in both ({len(same)}): average fill gap ${sum(gaps) / len(gaps):.3f} per contract, largest ${max(gaps):.2f}")
    p()
    p("Unpriced (no recorded quote for the contract near that minute): " +
      (", ".join(f"{c} at {t}" for (d, c), t in sorted(quotes.missing.items())) or "none"))
    open(os.path.join(out, "results.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwritten: {out}/results.txt")


if __name__ == "__main__":
    main()
