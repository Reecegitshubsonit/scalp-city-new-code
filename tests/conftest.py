from datetime import datetime, timedelta

import pytest

from scalpcity.types import Bar, ET


@pytest.fixture
def mk():
    """mk(ticker, 'HH:MM', close, high=None, low=None, volume=1000) -> Bar starting at that time on 2026-10-08."""
    def make(ticker, hhmm, close, high=None, low=None, volume=1000.0, day=(2026, 10, 8), open_=None):
        h, m = map(int, hhmm.split(":"))
        ts = datetime(*day, h, m, tzinfo=ET)
        return Bar(ticker, ts, open_ if open_ is not None else close,
                   high if high is not None else close, low if low is not None else close, close, volume)
    return make
