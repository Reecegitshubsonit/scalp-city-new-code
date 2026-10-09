from datetime import date

import pytest

from scalpcity.contracts import atm_strike, next_trading_day, occ_symbol, underlying_of
from scalpcity.indicators import Atr, Ema, IndicatorSet, SessionVwap


def test_ema_seeds_with_first_value_then_smooths():
    e = Ema(9)
    assert e.update(10.0) == 10.0
    assert e.update(20.0) == pytest.approx(12.0)  # alpha = 0.2


def test_atr_average_then_wilder(mk):
    a = Atr(2)
    assert a.update(mk("QQQ", "9:30", 10, high=11, low=9)) == 2.0
    assert a.update(mk("QQQ", "9:31", 10, high=12, low=10)) == 2.0  # avg(2, 2)
    # third bar: Wilder smoothing (2*1 + tr)/2, tr = max(1, |11-10|, |10-10|) = 1
    assert a.update(mk("QQQ", "9:32", 10, high=11, low=10)) == pytest.approx(1.5)


def test_vwap_is_volume_weighted_and_resets(mk):
    v = SessionVwap()
    v.update(mk("QQQ", "9:30", 10, volume=100))
    assert v.update(mk("QQQ", "9:31", 20, volume=300)) == pytest.approx(17.5)
    v.reset()
    assert v.value is None


def test_warm_feeds_emas_but_not_vwap(mk):
    s = IndicatorSet()
    s.warm(mk("QQQ", "15:59", 100))
    assert s.ema50.n == 1 and s.vwap.value is None
    s.update(mk("QQQ", "9:30", 101))
    assert s.vwap.value == 101


def test_squeeze_needs_atr_and_compares_gap(mk):
    s = IndicatorSet()
    assert s.squeezed(0.15) is False
    for i in range(30):
        s.warm(mk("QQQ", "10:00", 100.0, high=100.5, low=99.5))
    assert s.squeezed(0.15) is True  # flat price: EMA9 == EMA21


def test_occ_symbol_matches_webull_format():
    assert occ_symbol("SPY", date(2026, 10, 9), "CALL", 774.0) == "SPY261009C00774000"
    assert occ_symbol("QQQ", date(2026, 10, 9), "PUT", 748.0) == "QQQ261009P00748000"
    assert underlying_of("IWM261009C00278000") == "IWM"


def test_next_trading_day_skips_weekend_and_holiday():
    assert next_trading_day(date(2026, 10, 8)) == date(2026, 10, 9)   # Thu -> Fri
    assert next_trading_day(date(2026, 10, 9)) == date(2026, 10, 12)  # Fri -> Mon
    assert next_trading_day(date(2026, 9, 4)) == date(2026, 9, 8)     # Fri before Labor Day (Mon 9/7)


def test_atm_strike_rounds_to_dollar():
    assert atm_strike(747.58) == 748.0
