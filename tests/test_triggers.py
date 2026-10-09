import pytest

from scalpcity.indicators import IndicatorSet
from scalpcity.triggers import Ema50Cross, RangeBreak, VwapCross, charge


def ind_with_atr(mk, atr_bar=(101, 99), n=20):
    s = IndicatorSet()
    for _ in range(n):
        s.warm(mk("QQQ", "15:59", 100, high=atr_bar[0], low=atr_bar[1]))
    return s


def test_charge_matches_video_example():
    assert charge(0.6, 1.0) == 40.0
    assert charge(0.0, 1.0) == 100.0
    assert charge(2.0, 1.0) == 0.0


def test_vwap_cross_up_down_and_no_signal_on_first_bar(mk):
    ind, trig = ind_with_atr(mk), VwapCross(1.0)
    bars = [mk("QQQ", "9:30", 99, volume=100), mk("QQQ", "9:31", 98, volume=100), mk("QQQ", "9:32", 102, volume=100)]
    views = []
    for b in bars:
        ind.update(b)
        views.append(trig.update(b, ind))
    assert views[0].signal is None and views[1].signal is None   # first bar: close == VWAP is not a cross
    assert views[2].signal == "CALL"          # closed up through VWAP
    b = mk("QQQ", "9:33", 95, volume=100)
    ind.update(b)
    assert trig.update(b, ind).signal == "PUT"


def test_ema50_not_ready_until_50_samples(mk):
    trig = Ema50Cross(1.0)
    ind = IndicatorSet()
    for _ in range(10):
        ind.warm(mk("QQQ", "15:59", 100))
    view = trig.update(mk("QQQ", "9:30", 100), ind)
    assert view.ready is False and view.reason_code == "WARMING_UP"
    for _ in range(45):
        ind.warm(mk("QQQ", "15:59", 100))
    assert trig.update(mk("QQQ", "9:30", 100), ind).ready is True


def test_range_forms_then_breaks_once_per_crossing(mk):
    ind, trig = ind_with_atr(mk, (101, 99)), RangeBreak(1.0)
    for minute in range(30, 45):                       # 9:30..9:44 build the range 99..101
        v = trig.update(mk("QQQ", f"9:{minute}", 100, high=101, low=99), ind)
        assert v.ready is False and v.reason_code == "RANGE_FORMING"
    v = trig.update(mk("QQQ", "9:45", 100.5), ind)   # inside
    assert v.signal is None and v.charge_pct is not None and v.charge_pct < 100
    assert trig.update(mk("QQQ", "9:46", 101.5), ind).signal == "CALL"   # inside -> outside
    assert trig.update(mk("QQQ", "9:47", 102.0), ind).signal is None     # still outside: no re-fire
    assert trig.update(mk("QQQ", "9:48", 100.0), ind).signal is None     # back inside
    assert trig.update(mk("QQQ", "9:49", 98.0), ind).signal == "PUT"     # crossing the other side


def test_range_new_session_clears(mk):
    ind, trig = ind_with_atr(mk), RangeBreak(1.0)
    trig.update(mk("QQQ", "9:30", 100, high=101, low=99), ind)
    trig.new_session()
    assert trig.update(mk("QQQ", "9:50", 100), ind).reason_code == "NO_RANGE"
