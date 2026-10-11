from dataclasses import dataclass, field
from datetime import time

TICKERS = ("QQQ", "SPY", "IWM")


@dataclass(frozen=True)
class Settings:
    contracts: int = 10
    daily_goal: float = 600.0
    daily_loss: float = 100.0
    cooldown_s: int = 120
    last_entry: time = time(15, 30)
    flat_by: time = time(15, 55)
    stale_idle_s: int = 120
    stale_in_trade_s: int = 30
    flatten_after_stale_s: int = 300
    squeeze_atr: float = 0.15
    trend_side: bool = True  # trade every trigger in the EMA9/EMA21 direction instead of the cross direction
    stop_atr: float = 1.0
    target_atr: float = 2.0
    charge_range_atr: float = 1.0
    forming_min_charge: float = 30.0
    atr_period: int = 14
    max_spread_pct: float = 0.15
    cash_per_bot: float = 25_000.0
    half_spread: dict = field(default_factory=lambda: {"SPY": 0.01, "QQQ": 0.015, "IWM": 0.02})


@dataclass(frozen=True)
class BotSpec:
    trigger: str  # "vwap" | "ema50" | "range"
    arm: time  # bot is shown armed/watching from this time
    start: time  # first time an entry is allowed
    chop_filter: bool


BOT_SPECS = {
    "vwap": BotSpec("vwap", time(9, 30), time(9, 30), True),
    "ema50": BotSpec("ema50", time(9, 30), time(9, 30), False),
    "range": BotSpec("range", time(9, 40), time(9, 45), False),
}
