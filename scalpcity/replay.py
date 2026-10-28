from datetime import date

from .types import Bar


class ReplayFeed:
    """In-memory replay of underlying bars. bars[ticker] is a list of Bar sorted by ts."""

    def __init__(self, bars: dict):
        self.bars = {t: sorted(v, key=lambda b: b.ts) for t, v in bars.items()}

    def days(self) -> list[date]:
        return sorted({b.ts.date() for v in self.bars.values() for b in v})

    def warm_bars(self, day: date, n: int = 600) -> dict:   # same count as LiveFeed.startup
        out = {}
        for t, v in self.bars.items():
            prior = [b for b in v if b.ts.date() < day]
            out[t] = prior[-n:]
        return out

    def day_bars(self, day: date) -> list[Bar]:
        merged = [b for v in self.bars.values() for b in v if b.ts.date() == day]
        return sorted(merged, key=lambda b: (b.ts, b.ticker))


def run_replay(engine, feed: ReplayFeed, day: date) -> None:
    engine.log.reset(day)
    engine.start_session(day, feed.warm_bars(day))
    for bar in feed.day_bars(day):
        engine.on_bar(bar)
