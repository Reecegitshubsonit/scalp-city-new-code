from datetime import time

from scalpcity.config import BOT_SPECS, TICKERS, Settings


def test_defaults_match_the_spec():
    s = Settings()
    assert (s.contracts, s.daily_goal, s.daily_loss, s.cooldown_s) == (10, 600.0, 100.0, 120)
    assert (s.stale_idle_s, s.stale_in_trade_s, s.flatten_after_stale_s) == (120, 30, 300)
    assert s.last_entry == time(15, 30) and s.flat_by == time(15, 55)


def test_nine_bots_worth_of_specs_and_windows():
    assert TICKERS == ("QQQ", "SPY", "IWM") and set(BOT_SPECS) == {"vwap", "ema50", "range"}
    assert BOT_SPECS["range"].arm == time(9, 40) and BOT_SPECS["range"].start == time(9, 45)
    assert BOT_SPECS["vwap"].start == time(9, 30) and BOT_SPECS["ema50"].start == time(9, 30)
    assert BOT_SPECS["vwap"].chop_filter is True and BOT_SPECS["ema50"].chop_filter is False and BOT_SPECS["range"].chop_filter is False
