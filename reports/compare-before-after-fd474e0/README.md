# Strategy code before vs after commit fd474e0 (Sat 2026-10-10), 90-day replay

**What was compared**
- **before:** `scalpcity/` as of `fd474e0^`. Side = cross or break direction, the way Friday traded.
- **after:** `scalpcity/` as of HEAD (`fd474e0` strategy files). Side = EMA9 vs EMA21 (`trend_side=True`). Also adds sticky exit decisions, partial-fill accounting and quote fields on fills.

**How**
- Each version was exported to a scratch folder and replayed through its own engine with `backtest/replay_harness.py`. The copy used is `replay_harness_used.py`; it differs from the repo version only by a fallback for the older `Fill` signature.
- Data:
  - Underlying: `backtest/data/*_1m.json`, 2026-06-01 to 2026-10-07 (90 days).
  - Option prices: Alpaca 1-minute option bars. 237 bars the "before" run needed were fetched into a scratch copy of the cache; `data/cache` in the repo was not changed.
  - Fills: buy at ask + $0.01, sell at bid − $0.01, no fees, no latency.
- Settings are identical for both runs except `trend_side`. That includes the config defaults: daily loss lock $100 and daily goal $600 per bot, so each bot usually stops after 1–2 losing trades a day. **Friday's live run used a looser loss lock**, so trade counts here are lower than live.
- Entries rejected for no option quote: before 50, after 42.

**Files**
- `old/`, `new/`: harness outputs (summary, trades, daily P&L, rejects, params, run log, equity charts).
- `compare.py` → `compare.txt`: the comparison by period, trigger and ticker.

**Result**: see `compare.txt`.
