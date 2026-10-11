import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

pl = pytest.importorskip("polars")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backtest"))
import replay_harness as H  # noqa: E402
from scalpcity.config import Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.replay import run_replay
from scalpcity.types import ET, OrderIntent, Quote
from tests.test_engine_replay import DAY, flat_option_quotes, make_feed


def intent(kind):
    return OrderIntent("SPY-VWAP", "SPY", kind, "CALL", 10, "x", 700.0, contract="SPY261009C00700000")


def test_slippage_broker_prices_against_the_trader():
    b = H.SlippageBroker(quotes=None, slippage=0.02)
    q = Quote("SPY261009C00700000", datetime(2026, 10, 8, 10, tzinfo=ET), 2.00, 2.04)
    assert b.execute(intent("BUY_OPEN"), q.symbol, q, q.ts).price == 2.06
    assert b.execute(intent("SELL_CLOSE"), q.symbol, q, q.ts).price == 1.98


def test_slippage_broker_latency_reprices_later_and_fails_without_quote():
    later = Quote("C", datetime(2026, 10, 8, 10, 1, tzinfo=ET), 3.00, 3.02)

    class Q:
        def get(self, contract, ts):
            return later if ts == later.ts else None
    q = Quote("C", datetime(2026, 10, 8, 10, tzinfo=ET), 2.00, 2.02)
    fill = H.SlippageBroker(Q(), 0.0, latency_s=60).execute(intent("BUY_OPEN"), "C", q, q.ts)
    assert fill.price == 3.02 and fill.ts == later.ts
    assert H.SlippageBroker(Q(), 0.0, latency_s=30).execute(intent("BUY_OPEN"), "C", q, q.ts) is None


def test_extract_trades_matches_bot_pnl_and_applies_fees(tmp_path):
    log = EventLog(str(tmp_path), "replay")
    eng = Engine(Settings(), log, H.SlippageBroker(None, 0.0), flat_option_quotes())
    run_replay(eng, make_feed(), DAY)
    trades, _ = H.extract_trades(log.read(DAY), fee_per_contract=0.05)
    closed = [t for t in trades if t["pnl"] is not None]
    assert len(closed) == sum(b.trades for b in eng.bots) > 0
    for bot in eng.bots:
        gross = sum(t["pnl_gross"] for t in closed if t["bot"] == bot.bot_id)
        assert round(gross, 2) == bot.pnl_day
    t = closed[0]
    assert t["fees"] == round(0.05 * t["qty"] * 2, 2) and t["pnl"] == round(t["pnl_gross"] - t["fees"], 2)
    assert t["exit_reason"] in {"STOP", "TARGET", "TIME"}


def test_max_drawdown():
    assert H.max_drawdown([10, -5, -10, 20, -30]) == -30
    assert H.max_drawdown([1, 2, 3]) == 0


def write_alpaca_dump(path, bars):
    rows = [{"t": b.ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "o": b.open, "h": b.high, "l": b.low,
             "c": b.close, "v": b.volume, "n": 1, "vw": b.close} for b in bars]
    pre = bars[0].ts.replace(hour=8, minute=0)   # a pre-market bar the loader must drop
    rows.insert(0, {"t": pre.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "o": 1, "h": 1, "l": 1, "c": 1, "v": 1, "n": 1, "vw": 1})
    json.dump(rows, open(path, "w"))


def test_end_to_end_offline_writes_every_output(tmp_path):
    feed = make_feed()
    data, cache = tmp_path / "data", tmp_path / "cache"
    data.mkdir(), cache.mkdir()
    for t, bars in feed.bars.items():
        write_alpaca_dump(data / f"{t}_1m.json", bars)
    assert len(H.load_underlying(str(data / "SPY_1m.json"), "SPY", DAY, DAY)) == 780   # two RTH days, pre-market dropped

    # Cache flat 3.00 option bars for every contract the bots could pick on DAY.
    from scalpcity.contracts import atm_strike, next_trading_day, occ_symbol
    rows = [{"t": (datetime(2026, 10, 8, 9, 30, tzinfo=ET) + timedelta(minutes=i)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "c": 3.0} for i in range(390)]
    for t, bars in feed.bars.items():
        for strike in {atm_strike(b.close) for b in bars if b.ts.date() == DAY}:
            for right in ("CALL", "PUT"):
                c = occ_symbol(t, next_trading_day(DAY), right, strike)
                json.dump(rows, open(cache / f"option-{c}-{DAY}.json", "w"))

    out = H.main(["--start", str(DAY), "--end", str(DAY), "--offline", "--data-dir", str(data),
                  "--cache-dir", str(cache), "--out", str(tmp_path / "out"), "--set", "stop_atr=1.0"])
    for name in ("params.json", "trades.csv", "daily.csv", "rejects.csv", "summary.json", "run.log",
                 "equity_by_bot.png", "equity_total.png", f"events/{DAY}-replay.jsonl.gz"):
        assert os.path.exists(os.path.join(out, name)), name
    summary = json.load(open(os.path.join(out, "summary.json")))
    assert summary["total"]["trades"] > 0 and summary["option_bars_missing_offline"] == 0
    assert json.load(open(os.path.join(out, "params.json")))["settings"]["stop_atr"] == 1.0


def test_short_day_is_excluded_offline():
    feed = make_feed()
    bars = {t: [b for b in v if not (b.ts.date() == DAY and b.ts.hour == 12)] for t, v in feed.bars.items()}
    _, repaired, excluded = H.repair_short_days(bars, DAY, DAY, cache_dir="unused", offline=True)
    assert repaired == {} and excluded == [str(DAY)]
