import threading
from datetime import date

from .bot import Bot
from .config import BOT_SPECS, TICKERS, Settings
from .contracts import atm_strike, next_trading_day, occ_symbol
from .events import EventLog
from .indicators import IndicatorSet
from .risk import RiskGate
from .triggers import Ema50Cross5m, RangeBreak, VwapCross
from .types import Bar, OrderIntent

_TRIGGERS = {"vwap": VwapCross, "ema50": Ema50Cross5m, "range": RangeBreak}


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
                warm_up = getattr(bot.trigger, "warm_up", None)   # triggers with their own timeframe (5-minute EMA50)
                if warm_up is not None:
                    warm_up(warm_bars.get(bot.ticker, []))

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
            if self.day is not None and bar.ts.date() < self.day:
                return   # a previous session's bar (e.g. re-sent by the feed at the open) must never reach today's VWAP or triggers
            ind = self.ind[bar.ticker]
            ind.update(bar)
            for bot in [b for b in self.bots if b.ticker == bar.ticker]:
                out = bot.on_bar(bar, ind)
                if not out.intents:
                    held = self._held(bot, bar)
                    for ev in out.events:
                        if ev["kind"] == "tick":
                            ev.update(held)
                self._write(bar.end, bot, out.events)
                for intent in out.intents:
                    self._execute(bot, intent, bar, ind)

    def _held(self, bot: Bot, bar: Bar) -> dict:
        """Open position fields for the bar's tick, so the view can show side, stop/target progress and open P&L. Empty when flat."""
        p = bot.position
        if p is None or bot.pending is not None or p.entry_price is None or not p.contract:
            return {}
        held = {"side": p.right, "contract": p.contract, "qty": p.qty, "entry_price": p.entry_price,
                "entry_und": round(p.entry_und, 2), "stop_und": round(p.stop_und, 2), "target_und": round(p.target_und, 2)}
        try:
            quote = self.quotes.get(p.contract, bar.end)
        except Exception:   # a quote error must not stop the bar: the tick goes out without open P&L
            quote = None
        if quote is not None and quote.bid > 0 and quote.ask >= quote.bid:
            mid = (quote.bid + quote.ask) / 2
            held["option_mid"] = round(mid, 4)
            # realized_pnl holds the entry fee (and any partial exits); the exit fee is not known yet
            held["open_pnl"] = round(p.realized_pnl + (mid - p.entry_price) * p.qty * 100, 2)
        return held

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
        levels = {}
        if intent.kind == "BUY_OPEN" and bot.position is not None:   # so a restart rebuilds the same stop/target
            levels = {"stop_und": round(bot.position.stop_und, 4), "target_und": round(bot.position.target_und, 4)}
        self._write(bar.end, bot, [{"kind": "order_sent", "state": bot.state.value, "reason_code": intent.kind,
                                    "reason_text": f"{intent.kind} {intent.qty} {contract} bid/ask {quote.bid}/{quote.ask}",
                                    "inputs": inputs, "charge_pct": None, "contract": contract, "qty": intent.qty, **levels}])
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
