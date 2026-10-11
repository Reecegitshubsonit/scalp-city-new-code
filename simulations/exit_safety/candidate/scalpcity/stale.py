from .bot import State
from .live import market_open
from .types import OrderIntent


def check_stale(engine, now, last_bar_wall: dict, open_quote_wall: dict) -> None:
    """now / last_bar_wall / open_quote_wall are wall-clock datetimes.

    A ticker is stale when no new bar for stale_idle_s (market hours only). Entries are blocked for stale tickers
    through engine.stale. A bot in a trade is stale when its option quote is older than stale_in_trade_s, and is
    flattened once that age passes flatten_after_stale_s.
    """
    s = engine.s
    if not market_open(now):
        engine.stale.clear()
        return
    for ticker in engine.ind:
        seen = last_bar_wall.get(ticker)
        age = (now - seen).total_seconds() if seen else None
        is_stale = age is None or age > s.stale_idle_s
        if is_stale:
            engine.stale.add(ticker)
        else:
            engine.stale.discard(ticker)
        text = f"no bar for {int(age)}s" if age is not None else "no bars yet"
        for bot in [b for b in engine.bots if b.ticker == ticker and b.position is None]:
            engine._write(now, bot, bot.set_stale(is_stale, text))
    for bot in engine.bots:
        if bot.position is None or bot.pending == "entry":
            continue
        seen = open_quote_wall.get(bot.bot_id)
        age = (now - seen).total_seconds() if seen else None
        quote_stale = age is None or age > s.stale_in_trade_s
        engine._write(now, bot, bot.set_stale(quote_stale, f"option quote {int(age)}s old" if age is not None else "no option quote"))
        if quote_stale and age is not None and age > s.flatten_after_stale_s and bot.pending is None:
            bot.pending = "exit"
            bot._set(State.EXITING, "EXIT_STALE", "flattening: data stale too long")
            engine._write(now, bot, [bot._snapshot_event("state_change", {}, None)])
            intent = OrderIntent(bot.bot_id, bot.ticker, "SELL_CLOSE", bot.position.right, bot.position.qty, "STALE",
                                 bot.position.entry_und, contract=bot.position.contract)
            quote = engine.quotes.get(intent.contract, now)
            if quote is None:
                engine._write(now, bot, bot.on_order_failed("SELL_CLOSE", "NO_QUOTE"))
                continue
            fill = engine.broker.execute(intent, intent.contract, quote, now)
            engine._write(now, bot, bot.on_fill(fill, {}) if fill else bot.on_order_failed("SELL_CLOSE", "NO_FILL"))
