import uuid
from datetime import datetime

from .guard import SANDBOX_HOST
from .types import Bar, Quote
from .webull_parse import parse_bars, parse_occ, parse_snapshot


def _json(response):
    return response.json() if hasattr(response, "json") else response


class WebullClient:
    """Thin wrapper over the Webull SDK. `data` and `trade` are injectable for tests."""

    def __init__(self, data, trade):
        self.data, self.trade = data, trade

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
        resp = self.data.market_data.get_history_bar(ticker, "US_STOCK", "M1", count=str(count),
                                                     real_time_required=True, trading_sessions="RTH")
        return parse_bars(_json(resp), ticker)

    def option_quote(self, contract: str) -> tuple[Quote, int] | None:
        resp = self.data.option_market_data.get_option_snapshot(contract, "US_OPTION")
        return parse_snapshot(_json(resp), contract)

    # ---- account / orders ----
    def accounts(self) -> list[dict]:
        rows = _json(self.trade.account_v2.get_account_list())
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
        resp = self.trade.order_v2.place_option(account_id, order)
        status = getattr(resp, "status_code", 200)
        if status != 200:
            raise RuntimeError(f"place_option http {status}: {str(_json(resp))[:200]}")
        return client_order_id

    def order_detail(self, account_id: str, client_order_id: str) -> dict:
        return _json(self.trade.order_v2.get_order_detail(account_id, client_order_id))

    def cancel_option(self, account_id: str, client_order_id: str) -> None:
        self.trade.order_v2.cancel_option(account_id, client_order_id)
