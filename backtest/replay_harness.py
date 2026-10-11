"""Multi-day backtest: replays historical 1-minute bars through the live Engine and bots, unchanged.

Underlying bars come from backtest/data/{TICKER}_1m.json (regular hours only). Option prices come from
Alpaca 1-minute option trade bars, fetched on demand and cached under data/cache (read-only market data).
Fills: buy at modeled ask + slippage, sell at modeled bid - slippage, optionally priced `latency_s` after the
signal bar ends. Every run writes params, trades, daily P&L, summary, charts, per-day event logs and a run log
to its own output folder. Usage:

    .venv/bin/python backtest/replay_harness.py --start 2026-06-01 --end 2026-10-07 --slippage 0.01 --fee 0.0
"""
import argparse
import dataclasses
import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, time, timedelta

import polars as pl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scalpcity.config import TICKERS, Settings
from scalpcity.engine import Engine
from scalpcity.events import EventLog
from scalpcity.quotes import BarQuoteSource
from scalpcity.replay import ReplayFeed, run_replay
from scalpcity.types import ET, Bar, Fill, OrderIntent, Quote

log = logging.getLogger("replay_harness")


class SlippageBroker:
    """Buys at ask + slippage, sells at bid - slippage. With latency_s > 0 the quote is re-read that many seconds
    after the signal, so the fill uses the price the order would actually meet."""
    source = "modeled"

    def __init__(self, quotes, slippage: float = 0.0, latency_s: int = 0):
        self.quotes, self.slippage, self.latency = quotes, slippage, timedelta(seconds=latency_s)

    def execute(self, intent: OrderIntent, contract: str, quote: Quote, ts: datetime) -> Fill | None:
        if self.latency:
            quote = self.quotes.get(contract, ts + self.latency)
            if quote is None:
                return None
        if intent.kind == "BUY_OPEN":
            price = quote.ask + self.slippage
        else:
            price = max(0.01, quote.bid - self.slippage)
        if price <= 0:
            return None
        return Fill(intent.bot_id, intent.kind, contract, intent.qty, round(price, 2), self.source,
                    ts + self.latency, quote.bid, quote.ask)


def load_underlying(path: str, ticker: str, start: date, end: date) -> list[Bar]:
    """Regular-hours bars (09:30-15:59 ET bar starts) from an Alpaca bars JSON dump. Warm-up days before `start`
    are kept so indicators are ready on the first day."""
    df = (pl.read_json(path)
          .with_columns(pl.col("t").str.to_datetime(time_zone="UTC").dt.convert_time_zone("America/New_York").alias("ts"))
          .filter(pl.col("ts").dt.time().is_between(time(9, 30), time(15, 59)),
                  pl.col("ts").dt.date() >= start - timedelta(days=7), pl.col("ts").dt.date() <= end)
          .sort("ts"))
    return [Bar(ticker, ts.astimezone(ET), o, h, l, c, float(v))
            for ts, o, h, l, c, v in df.select("ts", "o", "h", "l", "c", "v").iter_rows()]


FULL_DAY_BARS = 390


def repair_short_days(bars: dict, start: date, end: date, cache_dir: str, offline: bool) -> tuple[dict, dict, list]:
    """A day with fewer than 390 regular-hours bars for any ticker (e.g. a dump fetched mid-session) is re-pulled
    from Alpaca through the shared cache. Offline, or if the re-pull is still short, the day is excluded."""
    counts: dict[tuple[str, date], int] = {}
    for t, v in bars.items():
        for b in v:
            counts[(t, b.ts.date())] = counts.get((t, b.ts.date()), 0) + 1
    days = sorted({d for (_, d) in counts if start <= d <= end})
    hist = None
    if not offline:
        from scalpcity.alpaca_history import AlpacaHistory
        hist = AlpacaHistory(cache_dir)
    repaired, excluded = {}, []
    for d in days:
        short = [t for t in bars if counts.get((t, d), 0) < FULL_DAY_BARS]
        if not short:
            continue
        for t in short:
            fresh = [b for b in hist.stock_bars(t, d) if b.ts.time() < time(16, 0)] if hist else []
            if len(fresh) >= FULL_DAY_BARS:
                bars[t] = sorted([b for b in bars[t] if b.ts.date() != d] + fresh, key=lambda b: b.ts)
                repaired[f"{t} {d}"] = {"had": counts.get((t, d), 0), "now": len(fresh)}
            else:
                excluded.append(str(d))
                log.warning("excluding %s: %s has %d bars", d, t, counts.get((t, d), 0))
                break
    return bars, repaired, sorted(set(excluded))


class CachedOptionCloses:
    """Wraps AlpacaHistory.option_closes with an in-memory cache; offline mode never hits the network."""

    def __init__(self, cache_dir: str, offline: bool):
        self.cache_dir, self.offline, self.mem = cache_dir, offline, {}
        self.fetched = self.missing = 0
        self.hist = None
        if not offline:
            from scalpcity.alpaca_history import AlpacaHistory
            self.hist = AlpacaHistory(cache_dir)

    def __call__(self, contract: str, ts: datetime):
        key = (contract, ts.date())
        if key not in self.mem:
            path = os.path.join(self.cache_dir, f"option-{contract}-{ts.date()}.json")
            cached = os.path.exists(path)
            if self.hist is not None:
                self.fetched += not cached
                rows = self.hist.option_closes(contract, ts.date())
            elif cached:
                rows = [(datetime.fromisoformat(r["t"].replace("Z", "+00:00")).astimezone(ET), r["c"]) for r in json.load(open(path))]
            else:
                self.missing += 1
                rows = []
            self.mem[key] = rows
        return self.mem[key]


def extract_trades(events: list[dict], fee_per_contract: float) -> tuple[list[dict], list[dict]]:
    """Round trips and order rejections from one day's event log. P&L is the bot's own number minus fees."""
    trades, rejects, open_ = [], [], {}
    exit_reason: dict[str, str] = {}
    for ev in events:
        bot, kind, code = ev["bot"], ev["kind"], ev.get("reason_code", "")
        if kind == "order_rejected":
            rejects.append({"time": ev["time"], "bot": bot, "reason": code, "contract": ev.get("contract")})
        elif kind == "state_change" and code.startswith("EXIT_") and code != "EXIT_RETRY":
            exit_reason[bot] = code[5:]
        elif kind == "fill" and code == "ENTRY_FILL":
            open_[bot] = {"bot": bot, "ticker": ev["ticker"], "contract": ev["contract"], "qty": ev["qty"],
                          "entry_time": ev["time"], "entry_price": ev["fill_price"], "entry_bid": ev.get("quote_bid"),
                          "entry_ask": ev.get("quote_ask"), "entry_und": ev["inputs"].get("price"), "atr": ev["inputs"].get("atr")}
        elif kind == "fill" and code == "EXIT_FILL" and bot in open_:
            open_[bot].update(exit_time=ev["time"], exit_price=ev["fill_price"], exit_bid=ev.get("quote_bid"),
                              exit_ask=ev.get("quote_ask"), exit_und=ev["inputs"].get("price"))
        elif kind == "trade_closed" and bot in open_:
            t = open_.pop(bot)
            fees = round(fee_per_contract * t["qty"] * 2, 2)
            t.update(exit_reason=exit_reason.pop(bot, ""), pnl_gross=ev["pnl"], fees=fees, pnl=round(ev["pnl"] - fees, 2))
            trades.append(t)
    for t in open_.values():   # entry filled but never closed by end of day: reported, not counted as P&L
        trades.append({**t, "exit_reason": "UNCLOSED", "pnl_gross": None, "fees": None, "pnl": None})
    return trades, rejects


def max_drawdown(series: list[float]) -> float:
    peak = cum = dd = 0.0
    for x in series:
        cum += x
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    return round(dd, 2)


def summarize(trades: pl.DataFrame, daily: pl.DataFrame) -> dict:
    closed = trades.filter(pl.col("pnl").is_not_null())

    def stats(df: pl.DataFrame, day_pnl: list[float]) -> dict:
        n = df.height
        if n == 0:
            return {"trades": 0}
        wins, losses = df.filter(pl.col("pnl") > 0), df.filter(pl.col("pnl") <= 0)
        gross_loss = -losses["pnl"].sum()
        return {"trades": n, "net_pnl": round(df["pnl"].sum(), 2), "gross_pnl_before_fees": round(df["pnl_gross"].sum(), 2),
                "fees": round(df["fees"].sum(), 2), "win_rate": round(wins.height / n, 4),
                "avg_pnl": round(df["pnl"].mean(), 2), "avg_win": round(wins["pnl"].mean(), 2) if wins.height else None,
                "avg_loss": round(losses["pnl"].mean(), 2) if losses.height else None,
                "profit_factor": round(wins["pnl"].sum() / gross_loss, 3) if gross_loss > 0 else None,
                "max_drawdown_daily": max_drawdown(day_pnl), "days_traded": len(day_pnl),
                "positive_days": sum(1 for x in day_pnl if x > 0),
                "by_exit_reason": {r["exit_reason"]: {"trades": r["n"], "pnl": round(r["pnl"], 2)}
                                   for r in df.group_by("exit_reason").agg(n=pl.len(), pnl=pl.col("pnl").sum()).iter_rows(named=True)}}

    out = {"total": stats(closed, daily.group_by("day").agg(pl.col("pnl").sum()).sort("day")["pnl"].to_list()),
           "unclosed_trades": trades.height - closed.height, "by_bot": {}}
    for bot in sorted(closed["bot"].unique().to_list()):
        out["by_bot"][bot] = stats(closed.filter(pl.col("bot") == bot), daily.filter(pl.col("bot") == bot).sort("day")["pnl"].to_list())
    return out


def plot(trades: pl.DataFrame, daily: pl.DataFrame, out_dir: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    closed = trades.filter(pl.col("pnl").is_not_null()).sort("exit_time")
    fig, ax = plt.subplots(figsize=(12, 6))
    for bot in sorted(closed["bot"].unique().to_list()):
        d = closed.filter(pl.col("bot") == bot)
        ax.plot(range(d.height), d["pnl"].cum_sum().to_list(), linewidth=1, label=bot)
    ax.set_xlabel("trade number (per bot)")
    ax.set_ylabel("cumulative P&L ($, after fees)")
    ax.axhline(0, color="grey", linewidth=0.5)
    ax.legend(fontsize=8, ncol=3)
    ax.set_title("Cumulative P&L per bot")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "equity_by_bot.png"), dpi=120)
    plt.close(fig)

    tot = daily.group_by("day").agg(pl.col("pnl").sum()).sort("day")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    a1.plot(tot["day"].to_list(), tot["pnl"].cum_sum().to_list(), color="black")
    a1.set_ylabel("cumulative P&L ($)")
    a1.set_title("All bots combined, by day")
    a1.axhline(0, color="grey", linewidth=0.5)
    a2.bar(tot["day"].to_list(), tot["pnl"].to_list(), color=["tab:green" if x > 0 else "tab:red" for x in tot["pnl"].to_list()])
    a2.set_ylabel("day P&L ($)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "equity_total.png"), dpi=120)
    plt.close(fig)


def git_state() -> dict:
    def run(*cmd):
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout.strip()
    diff = run("git", "diff", "HEAD", "--", "scalpcity")
    return {"commit": run("git", "rev-parse", "HEAD"), "scalpcity_dirty_files": run("git", "diff", "--name-only", "HEAD", "--", "scalpcity").split(),
            "scalpcity_diff_sha256": hashlib.sha256(diff.encode()).hexdigest() if diff else None}


def parse_overrides(pairs: list[str]) -> dict:
    fields = {f.name: f for f in dataclasses.fields(Settings)}
    out = {}
    for pair in pairs:
        k, v = pair.split("=", 1)
        if k not in fields:
            raise SystemExit(f"unknown Settings field: {k}")
        cur = getattr(Settings(), k)
        out[k] = (v.lower() in ("1", "true", "yes") if isinstance(cur, bool) else
                  time.fromisoformat(v) if isinstance(cur, time) else type(cur)(v))
    return out


def main(argv=None) -> str:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=date.fromisoformat, required=True)
    ap.add_argument("--end", type=date.fromisoformat, required=True)
    ap.add_argument("--slippage", type=float, default=0.01, help="$ per contract added to buys and taken from sells")
    ap.add_argument("--fee", type=float, default=0.0, help="$ per contract per side")
    ap.add_argument("--latency-s", type=int, default=0, help="seconds after bar end at which the fill is priced")
    ap.add_argument("--set", nargs="*", default=[], metavar="FIELD=VALUE", help="Settings overrides, e.g. stop_atr=0.75")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "backtest", "data"))
    ap.add_argument("--cache-dir", default=os.path.join(ROOT, "data", "cache"))
    ap.add_argument("--offline", action="store_true", help="never fetch option bars; uncached contracts get no quote")
    ap.add_argument("--out", default=None, help="output folder (default reports/replay-<timestamp>)")
    args = ap.parse_args(argv)

    out = args.out or os.path.join(ROOT, "reports", f"replay-{datetime.now():%Y-%m-%d-%H%M%S}")
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(out, "run.log")), logging.StreamHandler()])
    if not args.offline:
        env = os.path.join(ROOT, ".env")
        for raw in open(env):
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

    settings = Settings(**parse_overrides(args.set))
    bars = {t: load_underlying(os.path.join(args.data_dir, f"{t}_1m.json"), t, args.start, args.end) for t in TICKERS}
    bars, repaired, excluded = repair_short_days(bars, args.start, args.end, args.cache_dir, args.offline)
    feed = ReplayFeed(bars)
    days = [d for d in feed.days() if args.start <= d <= args.end and str(d) not in excluded]
    params = {"run_started": datetime.now().isoformat(), "argv": sys.argv if argv is None else argv,
              "start": str(args.start), "end": str(args.end), "days": len(days), "slippage": args.slippage,
              "fee_per_contract_side": args.fee, "latency_s": args.latency_s, "offline": args.offline,
              "settings": {k: (str(v) if isinstance(v, time) else v) for k, v in dataclasses.asdict(settings).items()},
              "underlying_files": {t: os.path.join(args.data_dir, f"{t}_1m.json") for t in TICKERS},
              "short_days_repaired_from_alpaca": repaired, "days_excluded_incomplete_data": excluded,
              "fill_model": "buy = option last close + half_spread + slippage; sell = close - half_spread - slippage; "
                            "option close = last Alpaca 1m trade bar ended at fill time, max 5 min old",
              "git": git_state()}
    json.dump(params, open(os.path.join(out, "params.json"), "w"), indent=2)
    log.info("output %s, %d days %s..%s", out, len(days), days[0] if days else None, days[-1] if days else None)

    closes = CachedOptionCloses(args.cache_dir, args.offline)
    quotes = BarQuoteSource(closes, settings.half_spread)
    broker = SlippageBroker(quotes, args.slippage, args.latency_s)
    elog = EventLog(os.path.join(out, "events"), "replay")
    all_trades, all_rejects, daily = [], [], []
    for i, day in enumerate(days, 1):
        engine = Engine(settings, elog, broker, quotes)
        run_replay(engine, feed, day)
        trades, rejects = extract_trades(elog.read(day), args.fee)
        all_trades += trades
        all_rejects += [{**r, "day": str(day)} for r in rejects]
        for bot in engine.bots:
            pnl = round(sum(t["pnl"] for t in trades if t["bot"] == bot.bot_id and t["pnl"] is not None), 2)
            daily.append({"day": day, "bot": bot.bot_id, "pnl": pnl,
                          "trades": sum(1 for t in trades if t["bot"] == bot.bot_id and t["pnl"] is not None)})
        path = elog.path_for(day)
        with open(path, "rb") as src, gzip.open(path + ".gz", "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.remove(path)
        log.info("day %d/%d %s trades=%d rejects=%d day_pnl=%.2f option_fetches=%d",
                 i, len(days), day, len(trades), len(rejects), sum(t["pnl"] or 0 for t in trades), closes.fetched)

    trade_schema = {"bot": pl.String, "ticker": pl.String, "contract": pl.String, "qty": pl.Int64, "entry_time": pl.String,
                    "entry_price": pl.Float64, "entry_bid": pl.Float64, "entry_ask": pl.Float64, "entry_und": pl.Float64,
                    "atr": pl.Float64, "exit_time": pl.String, "exit_price": pl.Float64, "exit_bid": pl.Float64,
                    "exit_ask": pl.Float64, "exit_und": pl.Float64, "exit_reason": pl.String, "pnl_gross": pl.Float64,
                    "fees": pl.Float64, "pnl": pl.Float64}
    tdf = pl.DataFrame(all_trades, schema=trade_schema)
    ddf = pl.DataFrame(daily, schema={"day": pl.Date, "bot": pl.String, "pnl": pl.Float64, "trades": pl.Int64})
    rdf = pl.DataFrame(all_rejects, schema={"time": pl.String, "bot": pl.String, "reason": pl.String, "contract": pl.String, "day": pl.String})
    tdf.write_csv(os.path.join(out, "trades.csv"))
    ddf.write_csv(os.path.join(out, "daily.csv"))
    rdf.write_csv(os.path.join(out, "rejects.csv"))
    summary = summarize(tdf, ddf)
    summary["rejects_by_reason"] = {r["reason"]: r["n"] for r in rdf.group_by("reason").agg(n=pl.len()).iter_rows(named=True)}
    summary["option_bars_fetched"], summary["option_bars_missing_offline"] = closes.fetched, closes.missing
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=2, default=str)
    if tdf.filter(pl.col("pnl").is_not_null()).height:
        plot(tdf, ddf, out)
    log.info("done: %s", os.path.join(out, "summary.json"))
    return out


if __name__ == "__main__":
    main()
