import threading
import time as _time
import uuid
from datetime import datetime

from .guard import SANDBOX_HOST
from .types import Bar, Quote
from .webull_parse import parse_bars, parse_occ, parse_snapshot


def _is_throttled(error: Exception) -> bool:
    text = str(error)
    return "429" in text or "TOO_MANY_REQUESTS" in text


def _rows(body) -> list[dict]:
    """Stock bar rows from a history response: [{symbol, result: [...]}] or a bare list of rows."""
    if isinstance(body, dict):
        body = body.get("result", [])
    if isinstance(body, list) and body and isinstance(body[0], dict) and "result" in body[0]:
        return body[0]["result"] or []
    return body if isinstance(body, list) else []


def _json(response):
    return response.json() if hasattr(response, "json") else response


class WebullClient:
    """Thin wrapper over the Webull SDK. `data` and `trade` are injectable for tests."""

    def __init__(self, data, trade, min_interval: float = 0.5, sleep=_time.sleep, clock=_time.monotonic,
                 background_gap: float = 1.0):
        self.data, self.trade = data, trade
        self.min_interval, self.sleep, self.clock = min_interval, sleep, clock
        self.background_gap = background_gap
        self._lock, self._last = threading.Lock(), None
        self._waiting = 0   # engine (foreground) calls queued for a slot; background calls yield to them

    def _call(self, fn, *args, background: bool = False, **kwargs):
        """Every Webull request goes through here: spaced by min_interval, and retried with backoff on HTTP 429.
        A background call (the data recorder) waits until no engine call is queued and background_gap has passed."""
        for attempt in range(5):
            if background:
                self._wait_for_quiet()
            else:
                with self._lock:
                    self._waiting += 1
            try:
                with self._lock:
                    if self._last is not None:
                        wait = self.min_interval - (self.clock() - self._last)
                        if wait > 0:
                            self.sleep(wait)
                    self._last = self.clock()
            finally:
                if not background:
                    with self._lock:
                        self._waiting -= 1
            try:
                return fn(*args, **kwargs)
            except Exception as error:
                if not _is_throttled(error) or attempt == 4:
                    raise
                self.sleep(1.5 * (attempt + 1))

    def _wait_for_quiet(self) -> None:
        while True:
            with self._lock:
                if self._waiting == 0 and (self._last is None or self.clock() - self._last >= self.background_gap):
                    return
            self.sleep(0.05)

    @classmethod
    def from_env(cls, env) -> "WebullClient":
        from webull.core.client import ApiClient
        from webull.data.data_client import DataClient
        from webull.trade.trade_client import TradeClient
        api = ApiClient(env["WEBULL_APP_KEY"], env["WEBULL_APP_SECRET"], "us")
        api.add_endpoint("us", SANDBOX_HOST)
        api._stream_logger_set = True   # no SDK console/file logging: it can print request headers
        api._file_logger_set = True
        return cls(DataClient(api), TradeClient(api))

    # ---- data ----
    def recent_bars(self, ticker: str, count: int = 3) -> list[Bar]:
        resp = self._call(self.data.market_data.get_history_bar, ticker, "US_STOCK", "M1", count=str(count),
                          real_time_required=True, trading_sessions="RTH")
        return parse_bars(_json(resp), ticker)

    def option_quote(self, contract: str) -> tuple[Quote, int] | None:
        resp = self._call(self.data.option_market_data.get_option_snapshot, contract, "US_OPTION")
        return parse_snapshot(_json(resp), contract)

    # ---- raw data for the recorder (background priority, rows exactly as Webull sends them) ----
    def stock_bars_raw(self, ticker: str, count: int) -> list[dict]:
        resp = self._call(self.data.market_data.get_history_bar, ticker, "US_STOCK", "M1", count=str(count),
                          real_time_required=True, trading_sessions="RTH", background=True)
        return _rows(_json(resp))

    def option_bars_raw(self, contracts: list[str], count: int) -> dict[str, list[dict]]:
        resp = self._call(self.data.option_market_data.get_option_history_bars, contracts, "US_OPTION", "M1",
                          count=str(count), real_time_required=True, background=True)
        body = _json(resp)
        body = body.get("result", []) if isinstance(body, dict) else body
        return {item["symbol"]: item.get("result") or [] for item in (body if isinstance(body, list) else [])
                if isinstance(item, dict) and "symbol" in item}

    def option_snapshots_raw(self, contracts: list[str]) -> list[dict]:
        resp = self._call(self.data.option_market_data.get_option_snapshot, contracts, "US_OPTION", background=True)
        body = _json(resp)
        return [r for r in (body if isinstance(body, list) else []) if isinstance(r, dict)]

    # ---- account / orders ----
    def accounts(self) -> list[dict]:
        rows = _json(self._call(self.trade.account_v2.get_account_list))
        return rows if isinstance(rows, list) else rows.get("data") or []

    def place_option(self, account_id: str, contract: str, side: str, qty: int, limit: float) -> str:
        underlying, expiry, right, strike = parse_occ(contract)
        client_order_id = uuid.uuid4().hex[:32]
        order = [{
            "client_order_id": client_order_id, "combo_type": "NORMAL", "order_type": "LIMIT", "quantity": str(qty),
            "limit_price": f"{limit:.2f}", "option_strategy": "SINGLE", "side": side, "time_in_force": "DAY",
            "entrust_type": "QTY",
            "orders": [{"side": side, "quantity": str(qty), "symbol": underlying, "strike_price": f"{strike:.1f}",
                        "init_exp_date": str(expiry), "instrument_type": "OPTION", "option_type": right, "market": "US"}],
        }]
        resp = self._call(self.trade.order_v2.place_option, account_id, order)
        status = getattr(resp, "status_code", 200)
        if status != 200:
            raise RuntimeError(f"place_option http {status}: {str(_json(resp))[:200]}")
        return client_order_id

    def order_detail(self, account_id: str, client_order_id: str) -> dict:
        return _json(self._call(self.trade.order_v2.get_order_detail, account_id, client_order_id))

    def cancel_option(self, account_id: str, client_order_id: str) -> None:
        self._call(self.trade.order_v2.cancel_option, account_id, client_order_id)
