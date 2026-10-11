import json
import os
import time
from datetime import date, datetime, timedelta

import requests

from .types import ET, Bar

URL_STOCK = "https://data.alpaca.markets/v2/stocks/bars"
URL_OPTION = "https://data.alpaca.markets/v1beta1/options/bars"


def parse_alpaca_rows(rows: list[dict], ticker: str) -> list[Bar]:
    return [Bar(ticker, datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(ET),
                r["o"], r["h"], r["l"], r["c"], r["v"]) for r in rows]


class AlpacaHistory:
    """Read-only historical data for replay. Caches every response on disk. Needs ALPACA keys in env."""

    def __init__(self, cache_dir: str, key: str | None = None, secret: str | None = None, session=None):
        self.cache = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.headers = {"APCA-API-KEY-ID": key or os.environ["ALPACA_API_KEY"],
                        "APCA-API-SECRET-KEY": secret or os.environ["ALPACA_SECRET_KEY"]}
        self.http = session or requests
        self._last = 0.0

    def _get(self, url: str, params: dict) -> dict:
        for attempt in range(6):
            wait = 0.4 - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            r = self.http.get(url, headers=self.headers, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (404, 422):
                return {"bars": {}}
            time.sleep(2 ** attempt)
        raise RuntimeError(f"alpaca {url} failed: {r.status_code}")

    def _paged(self, url: str, params: dict, symbol: str) -> list[dict]:
        rows, token = [], None
        while True:
            body = self._get(url, {**params, **({"page_token": token} if token else {})})
            rows += body.get("bars", {}).get(symbol, [])
            token = body.get("next_page_token")
            if not token:
                return rows

    def _cached(self, name: str, loader):
        path = os.path.join(self.cache, name + ".json")
        if os.path.exists(path):
            return json.load(open(path))
        data = loader()
        json.dump(data, open(path, "w"))
        return data

    def stock_bars(self, ticker: str, day: date) -> list[Bar]:
        start = datetime(day.year, day.month, day.day, 9, 30, tzinfo=ET).astimezone().isoformat()
        end = datetime(day.year, day.month, day.day, 16, 0, tzinfo=ET).astimezone().isoformat()
        rows = self._cached(f"stock-{ticker}-{day}", lambda: self._paged(
            URL_STOCK, dict(symbols=ticker, timeframe="1Min", start=start, end=end, feed="sip", limit=10000, adjustment="split"), ticker))
        return parse_alpaca_rows(rows, ticker)

    def option_closes(self, contract: str, day: date) -> list[tuple[datetime, float]]:
        rows = self._cached(f"option-{contract}-{day}", lambda: self._paged(
            URL_OPTION, dict(symbols=contract, timeframe="1Min", start=f"{day}T12:00:00Z", end=f"{day}T22:00:00Z", limit=10000), contract))
        return [(datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(ET), r["c"]) for r in rows]
