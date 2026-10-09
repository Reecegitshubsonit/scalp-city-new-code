"""Live paper run: Webull sandbox feed + paper orders + API server on http://127.0.0.1:8000
Start before 9:30 ET on a trading day, in a 3.11 venv:  .venv/bin/python scripts/run_live.py
"""
import os
import sys
import threading
import time
from datetime import datetime

import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.broker import ModeledBroker
from scalpcity.config import TICKERS, Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.guard import SANDBOX_HOST, assert_paper_only
from scalpcity.live import LiveFeed, LiveQuoteSource, market_open
from scalpcity.server import create_app
from scalpcity.types import ET
from scalpcity.webull_broker import WebullPaperBroker
from scalpcity.webull_client import WebullClient


def load_env(path=".env"):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def main():
    load_env()
    client = WebullClient.from_env(os.environ)
    account = assert_paper_only(os.environ, SANDBOX_HOST, client.accounts())
    settings, log = Settings(), EventLog("logs", "live")
    broker = WebullPaperBroker(client, account["account_id"], fallback=ModeledBroker())
    engine = Engine(settings, log, broker, LiveQuoteSource(client))
    feed = LiveFeed(client, TICKERS, lambda: datetime.now(ET))
    today = datetime.now(ET).date()
    prior, todays = feed.startup(today)
    engine.start_session(today, prior)
    engine.catch_up(todays)   # a mid-session start still gets the real VWAP and opening range
    app = create_app(log, lambda: datetime.now(ET).date(), engine.set_paused, [b.bot_id for b in engine.bots])
    threading.Thread(target=uvicorn.run, args=(app,), kwargs=dict(host="127.0.0.1", port=8000, log_level="warning"), daemon=True).start()
    print("Scalp City live (paper). Dashboard: http://127.0.0.1:8000   Ctrl+C to stop.", flush=True)
    quote_wall: dict[str, datetime] = {}
    while True:
        now = datetime.now(ET)
        if market_open(now):
            for bar in feed.poll():
                engine.on_bar(bar)
            for bot in engine.bots:
                if bot.position is not None and bot.position.contract:
                    if client.option_quote(bot.position.contract):
                        quote_wall[bot.bot_id] = now
        engine.check_stale(now, feed.last_bar_wall, quote_wall)
        time.sleep(5)


if __name__ == "__main__":
    main()
