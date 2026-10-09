import json
import pathlib
from datetime import date

import pytest

from scalpcity.guard import GuardError, SANDBOX_HOST, assert_paper_only
from scalpcity.webull_parse import parse_bars, parse_occ, parse_order_detail, parse_snapshot

FIX = pathlib.Path(__file__).parent / "fixtures" / "webull"
ENV = {"WEBULL_ENV": "sandbox", "WEBULL_SANDBOX_ACCOUNT_ATTESTED": "true", "WEBULL_PAPER_ACCOUNT_NUMBER": "ACC3J5B"}
ACCOUNTS = [{"account_number": "ACC3GT2", "account_id": "a"}, {"account_number": "ACC3J5B", "account_id": "b"}]


def test_guard_selects_matching_account():
    assert assert_paper_only(ENV, SANDBOX_HOST, ACCOUNTS)["account_id"] == "b"


@pytest.mark.parametrize("mutate,host", [
    ({"WEBULL_ENV": "prod"}, SANDBOX_HOST),
    ({"WEBULL_SANDBOX_ACCOUNT_ATTESTED": "false"}, SANDBOX_HOST),
    ({}, "api.webull.com"),
    ({"WEBULL_PAPER_ACCOUNT_NUMBER": "NOPE"}, SANDBOX_HOST),
    ({"WEBULL_PAPER_ACCOUNT_NUMBER": ""}, SANDBOX_HOST),
])
def test_guard_refuses(mutate, host):
    with pytest.raises(GuardError):
        assert_paper_only({**ENV, **mutate}, host, ACCOUNTS)


def test_parse_real_stock_bars_fixture():
    bars = parse_bars(json.loads((FIX / "stock_bars_QQQ.json").read_text()), "QQQ")
    assert len(bars) == 5 and bars == sorted(bars, key=lambda b: b.ts)
    assert bars[-1].ts.hour == 15 and bars[-1].ts.minute == 59 and bars[-1].close == 747.58


def test_parse_real_option_snapshot_fixture():
    quote, delay = parse_snapshot(json.loads((FIX / "option_snapshot.json").read_text()), "QQQ261009C00748000")
    assert (quote.bid, quote.ask, delay) == (2.92, 2.95, 0)
    assert quote.ts.tzinfo is not None


def test_parse_snapshot_none_without_bid_ask():
    assert parse_snapshot([{"bid": "", "ask": ""}], "X") is None


def test_parse_occ():
    assert parse_occ("SPY261009C00774000") == ("SPY", date(2026, 10, 9), "CALL", 774.0)
    with pytest.raises(ValueError):
        parse_occ("garbage")


def test_parse_order_detail_statuses():
    assert parse_order_detail({"orders": [{"status": "SUBMITTED"}]}) == ("SUBMITTED", None, None)
    assert parse_order_detail({"orders": [{"status": "filled", "filled_quantity": "10", "filled_price": "2.95"}]}) == ("FILLED", 10.0, 2.95)
