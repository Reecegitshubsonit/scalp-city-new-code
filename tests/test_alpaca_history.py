import json
from datetime import date

from scalpcity.alpaca_history import AlpacaHistory, parse_alpaca_rows


class FakeHttp:
    def __init__(self, pages): self.pages, self.calls = list(pages), 0
    def get(self, url, headers=None, params=None, timeout=None):
        self.calls += 1
        body = self.pages.pop(0)
        return type("R", (), {"status_code": 200, "json": lambda s: body})()


ROWS = [{"t": "2026-10-08T13:30:00Z", "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 10, "n": 1, "vw": 1.2}]


def test_parse_converts_utc_to_new_york():
    bar = parse_alpaca_rows(ROWS, "QQQ")[0]
    assert (bar.ts.hour, bar.ts.minute, bar.close, bar.ticker) == (9, 30, 1.5, "QQQ")


def test_pages_are_joined_and_cached(tmp_path):
    http = FakeHttp([{"bars": {"QQQ": ROWS}, "next_page_token": "t2"}, {"bars": {"QQQ": ROWS}}])
    hist = AlpacaHistory(str(tmp_path), key="k", secret="s", session=http)
    assert len(hist.stock_bars("QQQ", date(2026, 10, 8))) == 2 and http.calls == 2
    assert len(hist.stock_bars("QQQ", date(2026, 10, 8))) == 2 and http.calls == 2   # second call served from cache
