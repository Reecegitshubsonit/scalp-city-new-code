from datetime import date, datetime, timedelta

from scalpcity.broker import ModeledBroker
from scalpcity.config import Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog, build_snapshot
from scalpcity.quotes import BarQuoteSource
from scalpcity.replay import ReplayFeed, run_replay
from scalpcity.types import Bar, ET, Quote

DAY = date(2026, 10, 8)


def synth_bars(ticker, day, base, drift=0.0, wiggle=0.0):
    out, price = [], base
    t = datetime(day.year, day.month, day.day, 9, 30, tzinfo=ET)
    for i in range(390):
        price += drift + (wiggle if i % 2 == 0 else -wiggle)
        out.append(Bar(ticker, t + timedelta(minutes=i), price, price + 0.1, price - 0.1, price, 1000.0))
    return out


def make_feed():
    prev = date(2026, 10, 7)
    bars = {}
    for tk, base in (("QQQ", 748.0), ("SPY", 774.0), ("IWM", 278.0)):
        bars[tk] = synth_bars(tk, prev, base, drift=0.05) + synth_bars(tk, DAY, base + 20, drift=0.0, wiggle=0.6)
    return ReplayFeed(bars)


def flat_option_quotes():
    def bars_for(contract, ts):
        base = ts.replace(hour=9, minute=30, second=0, microsecond=0)
        return [(base + timedelta(minutes=i), 3.0) for i in range(390)]
    return BarQuoteSource(bars_for, Settings().half_spread)


def run_once(tmp_path, name):
    log = EventLog(str(tmp_path / name), "replay")
    eng = Engine(Settings(), log, ModeledBroker(), flat_option_quotes())
    run_replay(eng, make_feed(), DAY)
    return log, eng


def test_replay_is_deterministic_byte_for_byte(tmp_path):
    a, _ = run_once(tmp_path, "a")
    b, _ = run_once(tmp_path, "b")
    assert open(a.path_for(DAY)).read() == open(b.path_for(DAY)).read()
    assert len(a.read(DAY)) > 1000


def test_every_bot_logs_a_tick_every_bar_and_seq_is_gapless(tmp_path):
    log, eng = run_once(tmp_path, "a")
    events = log.read(DAY)
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    ticks = [e for e in events if e["kind"] == "tick" and e["bot"] == "QQQ-VWAP"]
    assert len(ticks) == 390
    assert {e["bot"] for e in events} == set(eng.by_id)


def test_snapshot_covers_all_nine_bots_with_reasons(tmp_path):
    log, _ = run_once(tmp_path, "a")
    snap = build_snapshot(log.read(DAY))
    assert len(snap["bots"]) == 9
    assert all(row["reason_code"] for row in snap["bots"].values())


def test_trades_have_matching_fills_and_pnl_adds_up(tmp_path):
    log, eng = run_once(tmp_path, "a")
    events = log.read(DAY)
    closed = [e for e in events if e["kind"] == "trade_closed"]
    for bot_id, bot in eng.by_id.items():
        mine = [e["pnl"] for e in closed if e["bot"] == bot_id]
        assert round(sum(mine), 2) == bot.pnl_day
    assert len(closed) >= 5, "synthetic day must actually produce trades or this test proves nothing"
    buys = [e for e in events if e["kind"] == "fill" and e["reason_code"] == "ENTRY_FILL"]
    sells = [e for e in events if e["kind"] == "fill" and e["reason_code"] == "EXIT_FILL"]
    assert len(buys) == len(sells) and all(e["fill_source"] == "modeled" for e in buys + sells)


def test_risk_gate_rejects_when_no_quote(tmp_path):
    log = EventLog(str(tmp_path / "c"), "replay")
    eng = Engine(Settings(), log, ModeledBroker(), BarQuoteSource(lambda c, t: [], Settings().half_spread))
    run_replay(eng, make_feed(), DAY)
    kinds = {e["kind"] for e in log.read(DAY)}
    assert "order_sent" not in kinds
    if "order_rejected" in kinds:
        assert {e["reason_code"] for e in log.read(DAY) if e["kind"] == "order_rejected"} == {"NO_QUOTE"}
