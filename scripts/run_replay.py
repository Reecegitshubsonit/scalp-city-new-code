"""Replay one past trading day through the engine. Read-only data. Usage: python scripts/run_replay.py 2026-10-07"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.alpaca_history import AlpacaHistory
from scalpcity.broker import ModeledBroker
from scalpcity.config import TICKERS, Settings
from scalpcity.contracts import HOLIDAYS
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.quotes import BarQuoteSource
from scalpcity.replay import ReplayFeed, run_replay


def load_env(path=".env"):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def prior_trading_days(day: date, n: int) -> list[date]:
    out, d = [], day
    while len(out) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5 and d not in HOLIDAYS:
            out.append(d)
    return sorted(out)


def main(day: date) -> None:
    load_env()
    settings = Settings()
    hist = AlpacaHistory("data/cache")
    bars = {t: [b for d in prior_trading_days(day, 2) + [day] for b in hist.stock_bars(t, d)] for t in TICKERS}
    quotes = BarQuoteSource(lambda contract, ts: hist.option_closes(contract, ts.date()), settings.half_spread)
    log = EventLog("logs", "replay")
    engine = Engine(settings, log, ModeledBroker(), quotes)
    run_replay(engine, ReplayFeed(bars), day)
    print(f"events: {len(log.read(day))}  file: {log.path_for(day)}")
    for bot in engine.bots:
        print(f"{bot.bot_id:10s} trades={bot.trades:2d} pnl={bot.pnl_day:9.2f} state={bot.state.value}/{bot.reason_code}")


if __name__ == "__main__":
    main(date.fromisoformat(sys.argv[1]))
