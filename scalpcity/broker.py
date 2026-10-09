from datetime import datetime

from .types import Fill, OrderIntent, Quote


class ModeledBroker:
    """Fills at the quote: buys at the ask, sells at the bid. Labelled 'modeled'."""
    source = "modeled"

    def execute(self, intent: OrderIntent, contract: str, quote: Quote, ts: datetime) -> Fill | None:
        price = quote.ask if intent.kind == "BUY_OPEN" else quote.bid
        if price <= 0:
            return None
        return Fill(intent.bot_id, intent.kind, contract, intent.qty, round(price, 2), self.source, ts)
