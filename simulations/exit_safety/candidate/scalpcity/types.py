from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Bar:
    ticker: str
    ts: datetime  # bar START, tz-aware ET
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def end(self) -> datetime:
        return self.ts + timedelta(minutes=1)


@dataclass(frozen=True)
class Quote:
    symbol: str
    ts: datetime
    bid: float
    ask: float


@dataclass(frozen=True)
class OrderIntent:
    bot_id: str
    ticker: str
    kind: str  # "BUY_OPEN" | "SELL_CLOSE"
    right: str  # "CALL" | "PUT"
    qty: int
    reason: str
    und_price: float
    contract: str | None = None  # set for SELL_CLOSE (the held contract)


@dataclass(frozen=True)
class Fill:
    bot_id: str
    kind: str
    contract: str
    qty: int
    price: float
    source: str  # "broker" | "broker_offmarket" | "modeled"; broker_offmarket = sandbox price outside the quote bid/ask
    ts: datetime
    quote_bid: float | None = None   # the bid/ask the order was priced from, so P&L can be recomputed either way
    quote_ask: float | None = None
