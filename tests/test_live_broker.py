import json
import pathlib
from datetime import datetime, timedelta
from types import SimpleNamespace

from scalpcity.broker import ModeledBroker
from scalpcity.live import LiveFeed, market_open
from scalpcity.types import Bar, ET, OrderIntent, Quote
from scalpcity.webull_broker import WebullPaperBroker
from scalpcity.webull_client import WebullClient

NOW = datetime(2026, 10, 8, 10, 5, 30, tzinfo=ET)


def bar(ticker, hh, mm, close=100.0):
    return Bar(ticker, datetime(2026, 10, 8, hh, mm, tzinfo=ET), close, close, close, close, 1.0)


class FakeBars:
    def __init__(self, rows): self.rows = rows
    def recent_bars(self, ticker, count): return list(self.rows.get(ticker, []))[-count:]


def test_live_feed_emits_only_completed_new_bars_once():
    rows = {"QQQ": [bar("QQQ", 10, 3), bar("QQQ", 10, 4), bar("QQQ", 10, 5)]}  # 10:05 bar ends 10:06 -> still forming
    clock = [NOW]
    feed = LiveFeed(FakeBars(rows), ["QQQ"], lambda: clock[0])
    assert [b.ts.minute for b in feed.poll()] == [3, 4]
    assert feed.poll() == []                                  # nothing new, nothing repeated
    rows["QQQ"].append(bar("QQQ", 10, 6))
    clock[0] = NOW + timedelta(seconds=40)                    # 10:06:10 -> the 10:05 bar is now complete
    assert [b.ts.minute for b in feed.poll()] == [5]
    assert feed.last_bar_wall["QQQ"] == NOW + timedelta(seconds=40)


def test_market_open_hours():
    assert market_open(datetime(2026, 10, 8, 9, 30, tzinfo=ET))
    assert not market_open(datetime(2026, 10, 8, 9, 29, tzinfo=ET))
    assert not market_open(datetime(2026, 10, 8, 16, 0, tzinfo=ET))
    assert not market_open(datetime(2026, 10, 10, 11, 0, tzinfo=ET))  # Saturday


class FakeWebull:
    def __init__(self, statuses, fail_place=False):
        self.statuses, self.fail_place, self.cancelled, self.placed = list(statuses), fail_place, [], []
    def place_option(self, account_id, contract, side, qty, limit):
        if self.fail_place: raise RuntimeError("sandbox rejects options")
        self.placed.append((contract, side, qty, limit)); return "oid1"
    def order_detail(self, account_id, oid):
        s = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return {"orders": [dict(s)]}
    def cancel_option(self, account_id, oid): self.cancelled.append(oid)


def intent(kind="BUY_OPEN"):
    return OrderIntent("QQQ-VWAP", "QQQ", kind, "CALL", 10, "signal", 748.0, contract="QQQ261009C00748000")


QUOTE = Quote("QQQ261009C00748000", NOW, 2.92, 2.95)


def test_paper_broker_fills_at_ask_and_labels_broker():
    fake = FakeWebull([{"status": "SUBMITTED"}, {"status": "FILLED", "filled_quantity": "10", "filled_price": "2.94"}])
    b = WebullPaperBroker(fake, "acct", sleep=lambda s: None)
    fill = b.execute(intent(), "QQQ261009C00748000", QUOTE, NOW)
    assert (fill.price, fill.qty, fill.source) == (2.94, 10, "broker")
    assert fake.placed == [("QQQ261009C00748000", "BUY", 10, 2.95)]


def test_paper_broker_sells_at_bid_and_cancels_on_timeout():
    fake = FakeWebull([{"status": "SUBMITTED"}])
    b = WebullPaperBroker(fake, "acct", fill_timeout_s=3, sleep=lambda s: None)
    assert b.execute(intent("SELL_CLOSE"), "QQQ261009C00748000", QUOTE, NOW) is None
    assert fake.placed[0][1:] == ("SELL", 10, 2.92) and fake.cancelled == ["oid1"]


def test_paper_broker_returns_none_on_terminal_reject():
    fake = FakeWebull([{"status": "REJECTED"}])
    assert WebullPaperBroker(fake, "a", sleep=lambda s: None).execute(intent(), "C", QUOTE, NOW) is None


def test_paper_broker_falls_back_to_modeled_when_place_fails():
    b = WebullPaperBroker(FakeWebull([{}], fail_place=True), "a", fallback=ModeledBroker())
    fill = b.execute(intent(), "QQQ261009C00748000", QUOTE, NOW)
    assert (fill.price, fill.source) == (2.95, "modeled")


def test_webull_client_parses_stock_bars_and_snapshot_from_real_fixtures():
    fix = pathlib.Path(__file__).parent / "fixtures" / "webull"
    stock = json.loads((fix / "stock_bars_QQQ.json").read_text())
    snap = json.loads((fix / "option_snapshot.json").read_text())
    data = SimpleNamespace(
        market_data=SimpleNamespace(get_history_bar=lambda *a, **k: SimpleNamespace(json=lambda: stock)),
        option_market_data=SimpleNamespace(get_option_snapshot=lambda *a, **k: SimpleNamespace(json=lambda: snap)))
    client = WebullClient(data, SimpleNamespace())
    assert len(client.recent_bars("QQQ", 5)) == 5
    quote, delay = client.option_quote("QQQ261009C00748000")
    assert (quote.bid, quote.ask, delay) == (2.92, 2.95, 0)


def test_paper_broker_books_fill_outside_market_at_the_quote():
    buy = FakeWebull([{"status": "FILLED", "filled_quantity": "10", "filled_price": "2.50"}])  # below bid
    f = WebullPaperBroker(buy, "a", sleep=lambda s: None).execute(intent(), "C", QUOTE, NOW)
    assert (f.price, f.source, f.quote_bid, f.quote_ask) == (2.95, "broker_offmarket", 2.92, 2.95)   # booked at the ask
    sell = FakeWebull([{"status": "FILLED", "filled_quantity": "10", "filled_price": "3.40"}])  # above ask
    f = WebullPaperBroker(sell, "a", sleep=lambda s: None).execute(intent(kind="SELL_CLOSE"), "C", QUOTE, NOW)
    assert (f.price, f.source) == (2.92, "broker_offmarket")                                         # booked at the bid
    inside = FakeWebull([{"status": "FILLED", "filled_quantity": "10", "filled_price": "2.94"}])
    f = WebullPaperBroker(inside, "a", sleep=lambda s: None).execute(intent(), "C", QUOTE, NOW)
    assert (f.price, f.source) == (2.94, "broker")


class FakeQuotes:
    def __init__(self, delay, age_s):
        self.delay, self.age = delay, age_s
    def option_quote(self, contract):
        return Quote(contract, NOW - timedelta(seconds=self.age), 2.92, 2.95), self.delay


def test_live_quote_source_refuses_delayed_or_stale_quotes():
    from scalpcity.live import LiveQuoteSource
    now = lambda: NOW
    assert LiveQuoteSource(FakeQuotes(0, 3), now).get("C", NOW) is not None
    assert LiveQuoteSource(FakeQuotes(15, 3), now).get("C", NOW) is None    # delayed feed
    assert LiveQuoteSource(FakeQuotes(0, 90), now).get("C", NOW) is None    # old quote


def test_paper_broker_survives_failed_status_polls():
    class Flaky(FakeWebull):
        def order_detail(self, account_id, oid):
            if not getattr(self, "n", 0):
                self.n = 1; raise RuntimeError("429 TOO_MANY_REQUESTS")
            return super().order_detail(account_id, oid)
    fake = Flaky([{"status": "FILLED", "filled_quantity": "10", "filled_price": "2.94"}])
    fill = WebullPaperBroker(fake, "a", sleep=lambda s: None).execute(intent(), "C", QUOTE, NOW)
    assert fill is not None and fill.price == 2.94
