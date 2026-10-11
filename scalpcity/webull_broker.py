import time as _time
from datetime import datetime

from .broker import ModeledBroker
from .types import Fill, OrderIntent, Quote
from .webull_parse import TERMINAL_FAILED, parse_order_detail


TOL = 0.011  # price tolerance outside bid/ask before a sandbox fill is flagged


class WebullPaperBroker:
    """Places a marketable LIMIT on the Webull sandbox and waits for the fill.

    Buys at the ask, sells at the bid. If placing fails (e.g. the sandbox rejects option orders), falls back to
    the ModeledBroker, which labels the fill 'modeled'. Not filled in time -> cancel and return None.
    The fill price is the sandbox's own. One outside the quote's bid/ask is booked at the quote (ask for buys,
    bid for sells) and labeled 'broker_offmarket'.
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
            try:
                status, qty, price = parse_order_detail(self.client.order_detail(self.account_id, order_id))
            except Exception:   # a throttled or failed poll is not a fill result: keep polling until the timeout
                status, qty, price = "UNKNOWN", None, None
            if status == "FILLED":
                px, source = round(price or limit, 2), self.source
                if not quote.bid - TOL <= px <= quote.ask + TOL:
                    # the sandbox reported a price outside the market: book it at the quote (ask for buys, bid for sells);
                    # the raw sandbox price stays in the broker's order history
                    px, source = limit, "broker_offmarket"
                return Fill(intent.bot_id, intent.kind, contract, int(qty or intent.qty), px, source, ts, quote.bid, quote.ask)
            if status in TERMINAL_FAILED:
                return None
            self.sleep(self.poll_s)
            waited += self.poll_s
        try:
            self.client.cancel_option(self.account_id, order_id)
        except Exception:
            pass
        return None
