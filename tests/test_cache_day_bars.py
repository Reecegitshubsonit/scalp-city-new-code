import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from cache_day_bars import days_missing
from scalpcity.types import ET


def _touch(path):
    open(path, "w").close()


def test_days_missing_skips_cached_and_unfinished_days(tmp_path):
    logs, cache = tmp_path / "logs", tmp_path / "cache"
    logs.mkdir(); cache.mkdir()
    for name in ("2026-10-09-live.jsonl", "2026-10-12-live.jsonl", "2026-10-13-live.jsonl", "engine-2026-10-13.out"):
        _touch(logs / name)
    for t in ("QQQ", "SPY", "IWM"):
        _touch(cache / f"stock-{t}-2026-10-09.json")
    _touch(cache / "stock-QQQ-2026-10-12.json")   # one ticker cached is not enough
    during = datetime(2026, 10, 13, 15, 50, tzinfo=ET)
    assert days_missing(str(logs), str(cache), during) == [date(2026, 10, 12)]
    after = datetime(2026, 10, 13, 16, 20, tzinfo=ET)
    assert days_missing(str(logs), str(cache), after) == [date(2026, 10, 12), date(2026, 10, 13)]
