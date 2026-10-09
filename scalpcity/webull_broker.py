import time as _time
from datetime import datetime

from .broker import ModeledBroker
from .types import Fill, OrderIntent, Quote
from .webull_parse import TERMINAL_FAILED, parse_order_detail


class WebullPaperBroker:
    """Places a marketable LIMIT on the Webull sandbox and waits for the fill.

    Buys at the ask, sells at the bid. If placing fails (e.g. the sandbox rejects option orders), falls back to
    the ModeledBroker, which labels the fill 'modeled'. Not filled in time -> cancel and return None.
    """
    source = "broker"

    def __init__(self, client, account_id: str, fill_timeout_s: float = 15.0, poll_s: float = 1.0,
                 sleep=_time.sleep, fallback: ModeledBroker | None = None):
        self.client, self.account_id = client, account_id
        self.fill_timeout_s, self.poll_s, self.sleep = fill_timeout_s, poll_s, sleep
        self.fallback = fallback

    def execute(self, intent: OrderIntent, contract: str, quote: Quote, ts: datetime) -> Fill | None:
        side = "BUY" if intent.kind == "BUY_OPEN" else "SELL"
        limit = quote.ask if side == "BUY" else quote.bid
        try:
            order_id = self.client.place_option(self.account_id, contract, side, intent.qty, limit)
        except Exception:
            return self.fallback.execute(intent, contract, quote, ts) if self.fallback else None
        waited = 0.0
        while waited <= self.fill_timeout_s:
            status, qty, price = parse_order_detail(self.client.order_detail(self.account_id, order_id))
            if status == "FILLED":
                return Fill(intent.bot_id, intent.kind, contract, int(qty or intent.qty), round(price or limit, 2), self.source, ts)
            if status in TERMINAL_FAILED:
                return None
            self.sleep(self.poll_s)
            waited += self.poll_s
        self.client.cancel_option(self.account_id, order_id)
        return None
