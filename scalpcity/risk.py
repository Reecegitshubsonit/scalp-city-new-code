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

    def entry_risk(self, intent: OrderIntent, quote: Quote | None, stop_dist: float | None) -> float | None:
        """Estimated dollars lost if the entry hits its 1-ATR underlying stop: stop distance * risk_per_und_dollar
        * qty * 100, never more than the premium paid at the ask. None when it cannot be estimated."""
        if not stop_dist or stop_dist <= 0 or intent.qty <= 0:
            return None
        est = stop_dist * self.s.risk_per_und_dollar * intent.qty * 100
        if quote is not None and quote.ask > 0:
            est = min(est, quote.ask * intent.qty * 100)
        return round(est, 2)

    def check_room(self, est_risk: float | None, room: float) -> tuple[bool, str]:
        """Engine-wide loss cap: refuse an entry whose estimated stop loss exceeds the room left (unknown risk = refuse)."""
        if room <= 0:
            return False, "ENGINE_DAILY_LOSS"
        if est_risk is None:
            return False, "RISK_UNKNOWN"
        if est_risk > room:
            return False, "LOSS_ROOM"
        return True, ""
