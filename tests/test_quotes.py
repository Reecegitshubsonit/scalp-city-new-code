from datetime import datetime, timedelta

from scalpcity.quotes import BarQuoteSource
from scalpcity.types import ET

T0 = datetime(2026, 10, 8, 10, 0, tzinfo=ET)


def src(rows, hs=None):
    return BarQuoteSource(lambda c, t: rows, hs or {"QQQ": 0.015})


def test_uses_last_completed_bar_and_modeled_half_spread():
    rows = [(T0 - timedelta(minutes=2), 3.00), (T0 - timedelta(minutes=1), 3.10), (T0, 9.99)]
    q = src(rows, {"QQQ": 0.02}).get("QQQ261009C00748000", T0)
    assert (q.bid, q.ask) == (3.08, 3.12)


def test_none_when_no_completed_bar_or_too_stale():
    assert src([(T0, 3.0)]).get("QQQ261009C00748000", T0) is None
    assert src([(T0 - timedelta(minutes=30), 3.0)]).get("QQQ261009C00748000", T0) is None
