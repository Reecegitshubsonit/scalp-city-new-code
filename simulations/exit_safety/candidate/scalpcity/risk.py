from .config import Settings
from .types import OrderIntent, Quote


class RiskGate:
    """The only path to the broker. Entries are checked; exits always pass."""

    def __init__(self, settings: Settings):
        self.s = settings

    def check(self, intent: OrderIntent, quote: Quote | None, stale_tickers: set, halted: bool = False) -> tuple[bool, str]:
        if intent.kind == "SELL_CLOSE":
            return True, ""
        if halted:
            return False, "HALTED"
        if intent.ticker in stale_tickers:
            return False, "STALE_DATA"
        if intent.qty > self.s.contracts:
            return False, "SIZE_LIMIT"
        if quote is None:
            return False, "NO_QUOTE"
        if quote.bid <= 0 or quote.ask <= 0 or quote.ask < quote.bid:
            return False, "BAD_QUOTE"
        if (quote.ask - quote.bid) / quote.ask > self.s.max_spread_pct:
            return False, "WIDE_SPREAD"
        if quote.ask * intent.qty * 100 > self.s.cash_per_bot:
            return False, "CASH_LIMIT"
        return True, ""
