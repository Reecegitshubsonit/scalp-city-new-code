from dataclasses import dataclass, field
from datetime import time

TICKERS = ("QQQ", "SPY", "IWM")

# Display name of this engine (~/scalp-city, port 8010): dashboard, API and startup banner.
ENGINE_NAME = "Scalp City V2"

# Which way a bot trades when its trigger fires. Every BotSpec must name one; there is no global switch.
#   "trend": require EMA9/EMA21 agreement with the trigger; otherwise skip (never flip/fade)
#   "own":   the trigger's own direction (cross up = CALL, cross down = PUT), exempt from the trend filter
SIDE_RULES = ("trend", "own")


@dataclass(frozen=True)
class Settings:
    contracts: int = 10
    daily_goal: float = 600.0
    daily_loss: float = 800.0   # ENGINE-WIDE (live passes --daily-loss 800): the whole engine's realized loss cap for the session (all bots summed)
    cooldown_s: int = 120
    # Tickers exempt from the daily_loss cap (2026-11-06, Reece): never locked by it and, on the new code, never
    # refused for loss room. The daily_goal profit lock still applies to them.
    loss_cap_exempt: tuple = ("QQQ",)
    # US/Eastern bar end times. No new entries from 11:00:00 ET (last entry on the bar ending 10:59). A trade already
    # open is NOT closed at 11:00: it runs to its stop, its target, or the 15:55 ET end-of-day flatten.
    last_entry: time = time(10, 59)
    no_entry_from: time = time(11, 0)
    flat_by: time = time(15, 55)
    stale_idle_s: int = 120
    stale_in_trade_s: int = 30
    flatten_after_stale_s: int = 300
    squeeze_atr: float = 0.15
    stop_atr: float = 1.0
    target_atr: float = 2.0   # used only when trail_enabled is False
    # Scalp City V2 exit (2026-11-11, Reece; backtest cell none_trail1.5_arm0.5 in /workspace/exit-grid on the box):
    # keep the 1 ATR initial stop, NO fixed target. Once a bar close is trail_arm_atr x the 1-minute ATR at entry in the
    # trade's favor (puts mirrored), the stop trails trail_atr x the CURRENT 1-minute ATR behind the best close since
    # entry, ratchets only in the trade's favor and never sits looser than the initial stop. Checked on bar closes.
    trail_enabled: bool = True
    trail_atr: float = 1.5
    trail_arm_atr: float = 0.5
    charge_range_atr: float = 1.0
    forming_min_charge: float = 30.0
    atr_period: int = 14
    max_spread_pct: float = 0.15
    cash_per_bot: float = 25_000.0
    # Estimated dollars lost per contract per $1 the underlying moves against the trade, used to price a
    # 1-ATR stop for the engine-wide remaining-room check. 0.75 = median realized loser on Webull paper
    # (390 trades, incl. close-based overshoot and spread); theoretical ATM delta alone would be 0.5.
    risk_per_und_dollar: float = 0.75
    # 5-minute EMA50 contracts when the 1-minute ATR is unavailable (normally sized 10 * atr_1m / atr_5m)
    ema50_fallback_contracts: int = 4
    half_spread: dict = field(default_factory=lambda: {"SPY": 0.01, "QQQ": 0.015, "IWM": 0.02})


@dataclass(frozen=True)
class BotSpec:
    trigger: str  # "vwap" | "ema50" | "range"
    arm: time  # bot is shown armed/watching from this time
    start: time  # first time an entry is allowed
    chop_filter: bool
    side: str  # side rule, one of SIDE_RULES; required so no bot's direction depends on a hidden default
    last_entry: time | None = None  # last time an entry is allowed for this bot; None = Settings.last_entry

    def __post_init__(self):
        if self.side not in SIDE_RULES:
            raise ValueError(f"BotSpec {self.trigger}: side must be one of {SIDE_RULES}, got {self.side!r}")


BOT_SPECS = {
    "vwap": BotSpec("vwap", time(9, 30), time(9, 30), True, side="trend"),
    # 5-minute EMA50 cross traded in its own direction, 10:00-11:00 ET only (no entries from the bar ending 11:00 on)
    "ema50": BotSpec("ema50", time(10, 0), time(10, 0), False, side="own", last_entry=time(10, 59)),
    "range": BotSpec("range", time(9, 40), time(9, 45), False, side="trend"),
}
