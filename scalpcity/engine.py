import threading
from datetime import date

from .bot import Bot
from .config import BOT_SPECS, TICKERS, Settings
from .contracts import atm_strike, next_trading_day, occ_symbol
from .events import EventLog
from .indicators import IndicatorSet
from .risk import RiskGate
from .triggers import Ema50Cross, RangeBreak, VwapCross
from .types import Bar, OrderIntent

_TRIGGERS = {"vwap": VwapCross, "ema50": Ema50Cross, "range": RangeBreak}


def build_bots(settings: Settings) -> list[Bot]:
    return [Bot(t, spec, _TRIGGERS[key](settings.charge_range_atr), settings)
            for t in TICKERS for key, spec in BOT_SPECS.items()]


class Engine:
    def __init__(self, settings: Settings, log: EventLog, broker, quotes, risk: RiskGate | None = None, bots=None):
        self.s, self.log, self.broker, self.quotes = settings, log, broker, quotes
        self.risk = risk or RiskGate(settings)
        self.bots = bots or build_bots(settings)
        self.by_id = {b.bot_id: b for b in self.bots}
        self.ind = {t: IndicatorSet(settings.atr_period) for t in TICKERS}
        self.stale: set[str] = set()
        self.halted = False
        self.day: date | None = None
        # Live: the bar loop, the stale checks and the pause endpoint all touch the engine from different threads.
        self.lock = threading.RLock()

    def start_session(self, day: date, warm_bars: dict) -> None:
        with self.lock:
            self.day = day
            for ticker in self.ind:
                self.ind[ticker] = IndicatorSet(self.s.atr_period)
                for bar in warm_bars.get(ticker, []):
                    self.ind[ticker].warm(bar)
            for bot in self.bots:
                bot.new_session()

    def catch_up(self, bars) -> None:
        """Mid-session start: rebuild VWAP, EMAs, ATR and trigger state from today's completed bars. Never trades or logs."""
        with self.lock:
            for bar in sorted(bars, key=lambda b: (b.ts, b.ticker)):
                ind = self.ind[bar.ticker]
                ind.update(bar)
                for bot in self.bots:
                    if bot.ticker == bar.ticker:
                        bot.trigger.update(bar, ind)

    def recover(self, events: list) -> None:
        """Restart: rebuild each bot's day P&L, trades, cooldown and open position from today's event log. Writes nothing."""
        with self.lock:
            for ev in events:
                bot = self.by_id.get(ev.get("bot"))
                if bot is not None:
                    bot.restore(ev)
            for bot in self.bots:
                bot.finish_restore()

    def _write(self, time, bot, events: list) -> None:
        for ev in events:
            ev = dict(ev)
            self.log.append(time, bot.bot_id, bot.ticker, ev.pop("kind"), ev.pop("state", ""), ev.pop("reason_code", ""),
                            ev.pop("reason_text", ""), ev.pop("inputs", None), ev.pop("charge_pct", None), **ev)

    def on_bar(self, bar: Bar) -> None:
        with self.lock:
            ind = self.ind[bar.ticker]
            ind.update(bar)
            for bot in [b for b in self.bots if b.ticker == bar.ticker]:
                out = bot.on_bar(bar, ind)
                self._write(bar.end, bot, out.events)
                for intent in out.intents:
                    self._execute(bot, intent, bar, ind)

    def _execute(self, bot: Bot, intent: OrderIntent, bar: Bar, ind: IndicatorSet) -> None:
        if intent.kind == "BUY_OPEN":
            expiry = next_trading_day(bar.ts.date())
            contract = occ_symbol(intent.ticker, expiry, intent.right, atm_strike(bar.close))
        else:
            contract = intent.contract
        quote = self.quotes.get(contract, bar.end)
        inputs = ind.as_dict()
        if intent.kind == "BUY_OPEN":
            ok, why = self.risk.check(intent, quote, self.stale, self.halted)
            if not ok:
                self._write(bar.end, bot, [{"kind": "order_rejected", "state": bot.state.value, "reason_code": why,
                                            "reason_text": f"risk gate refused entry: {why}", "inputs": inputs, "charge_pct": None, "contract": contract}])
                self._write(bar.end, bot, bot.on_order_failed("BUY_OPEN", why))
                return
        elif quote is None:
            self._write(bar.end, bot, [{"kind": "order_rejected", "state": bot.state.value, "reason_code": "NO_QUOTE",
                                        "reason_text": "no quote to exit; retrying next bar", "inputs": inputs, "charge_pct": None, "contract": contract}])
            self._write(bar.end, bot, bot.on_order_failed("SELL_CLOSE", "NO_QUOTE"))
            return
        self._write(bar.end, bot, [{"kind": "order_sent", "state": bot.state.value, "reason_code": intent.kind,
                                    "reason_text": f"{intent.kind} {intent.qty} {contract} bid/ask {quote.bid}/{quote.ask}",
                                    "inputs": inputs, "charge_pct": None, "contract": contract, "qty": intent.qty}])
        try:
            fill = self.broker.execute(intent, contract, quote, bar.end)
        except Exception:   # a broker error must not leave the bot waiting on an order, or skip the other bots on this bar
            fill = None
        if fill is None:
            self._write(bar.end, bot, bot.on_order_failed(intent.kind, "NO_FILL"))
            return
        self._write(bar.end, bot, bot.on_fill(fill, inputs))

    def check_stale(self, now, last_bar_wall: dict, open_quote_wall: dict | None = None) -> None:
        """Live only. Implemented in scalpcity/stale.py (plan Task 11)."""
        from .stale import check_stale
        with self.lock:
            check_stale(self, now, last_bar_wall, open_quote_wall or {})

    def set_paused(self, bot_id: str, paused: bool, time) -> None:
        with self.lock:
            bot = self.by_id[bot_id]
            self._write(time, bot, bot.set_paused(paused))
