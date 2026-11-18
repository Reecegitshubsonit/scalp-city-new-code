# Option-premium model fitted on our own data — and a correction

Run 2026-11-17. Script `backtest/premium_fit_ours.py`, raw output `fit.json`.

This refits, on Scalp City's own record, the model previously fitted on Nick Fischer's
published Discord fills. **The conclusion from his data does not survive. See section 4.**

Model, premium in dollars per share:

    d_premium = delta_eff × favourable_underlying_move + decay_per_min × minutes + intercept

## 1. Two independent fits

**A. Fill fit** — our Webull sandbox paper trades, restricted to `broker>broker` fills
(576 of 728 closed trades). Each row carries the option price and the underlying price at both
ends, so unlike the fit on his feed there is no bar-alignment guesswork.

| Group | n | delta_eff | decay/min | intercept | R² |
|---|---:|---:|---:|---:|---:|
| ALL | 576 | 0.486 | −0.003 | +0.023 | **0.919** |
| QQQ | 140 | 0.482 | −0.005 | +0.061 | 0.921 |
| SPY | 162 | 0.481 | −0.003 | +0.021 | 0.929 |
| IWM | 274 | 0.520 | −0.002 | +0.008 | 0.911 |
| Scalp City V2 | 524 | 0.484 | −0.004 | +0.025 | 0.917 |
| new Scalp City | 52 | 0.491 | +0.001 | +0.018 | 0.934 |
| offmarket/modeled fills | 151 | 0.472 | −0.005 | +0.003 | 0.903 |

**B. Market fit** — raw Webull 1-minute option bars against 1-minute stock bars, 567,242
minute-pairs, no trades involved at all.

| Group | n | delta_eff | decay/min | intercept | R² |
|---|---:|---:|---:|---:|---:|
| ALL | 567,242 | 0.414 | −0.004 | +0.003 | 0.593 |
| QQQ | 256,780 | 0.410 | −0.007 | +0.006 | 0.599 |
| SPY | 216,406 | 0.426 | −0.003 | +0.002 | 0.591 |
| IWM | 94,056 | 0.366 | −0.002 | +0.002 | 0.500 |

R² of 0.92 on the fill fit against 0.47 on his data is the difference exact fill prices make.

**Use delta_eff ≈ 0.41, from the market fit.** The fill fit's 0.49 is biased upward: our exits
are triggered *by* premium reaching a stop or target level, so fitting on realised trades
selects on the dependent variable. The same endogeneity makes both intercepts useless as a
cost estimate — ours comes out positive (+0.023), which would mean our fills gain money from
nowhere. They do not; the estimator is wrong for that purpose.

## 2. Execution cost, measured directly instead

Since the intercept cannot carry it, the cost was measured from real quotes:
`data/webull/<day>/snapshots.jsonl`, all days 10/09–11/17, restricted to the $0.50–$20 premium
band the engines actually trade.

| Ticker | Quotes | Median spread | Median relative |
|---|---:|---:|---:|
| QQQ | 98,922 | $0.0200 | 0.50% |
| SPY | 98,842 | $0.0100 | 0.48% |
| IWM | 93,935 | $0.0200 | 1.19% |

Converting to ATR units, with a round trip crossing one full spread:

| Ticker | delta_eff | Median ATR | $ per 1 ATR | Spread | **COST_R** |
|---|---:|---:|---:|---:|---:|
| QQQ | 0.410 | 0.520 | 0.213 | 0.0200 | **0.094** |
| SPY | 0.426 | 0.298 | 0.127 | 0.0100 | **0.079** |
| IWM | 0.366 | 0.174 | 0.064 | 0.0200 | **0.313** |
| ALL | 0.414 | 0.247 | 0.102 | 0.0200 | **0.196** |

## 3. The finding that matters: IWM costs 3–4× what QQQ costs

In absolute terms IWM's spread is the same two cents as QQQ's. In ATR terms it is **0.313 R
against QQQ's 0.094 R**, because IWM's 1-minute ATR is a third of QQQ's. Every IWM trade
starts a third of an ATR behind before the strategy does anything.

IWM is also our most-traded ticker: 272 of 637 closed V2 trades, against 166 QQQ. We are
trading the most expensive instrument most often, and it is plausibly a large part of why the
paper record is negative. This is worth testing directly and has not been tested yet.

## 4. Correction to the Nick Fisher City report

`/home/ronaldsecret/nick-fisher-city/reports/premium-model-and-comparison.md` concluded, from
his feed, that the true per-trade drag was about **0.55 R**, and therefore that every exit-grid
result produced on 2026-11-17 was optimistic.

**That is wrong, and it should not be used.** Our own data gives **0.196 R in aggregate**, so
the `COST_R = 0.2` already assumed in `backtest/filters.py` and `backtest/trail_grid.py` is
close to right on average. The exit-grid rankings stand as reported.

His figure was inflated by the artifact documented in that same report: a quarter of his
round trips open and close inside one minute, which forces their entire premium change into
the intercept. Fitting a cost on data with that property overstates it. The proper response to
an unexplained intercept is to find the mechanism, not to adopt the number.

What is still true from that report: the per-day comparison, the 98% win rate on his
same-minute trades, and the conclusion that his feed is evidence of what his software prints
rather than of executed fills.

## 5. What is worth changing here

- `COST_R = 0.2` pooled is fine. **A single pooled constant is not.** Per-ticker costs of
  0.094 / 0.079 / 0.313 belong in `backtest/filters.py` and `backtest/trail_grid.py`, and
  re-running the exit grid with them is the obvious next test.
- `Settings.half_spread` in `scalpcity/config.py` holds QQQ 0.015, SPY 0.01, IWM 0.02 as half
  spreads. Measured full spreads are 0.020 / 0.010 / 0.020, so the half-spreads should be
  0.010 / 0.005 / 0.010. QQQ and IWM are currently overstated by 50% and 100%.
- `risk_per_und_dollar = 0.75` is documented as the median realised loss per contract per $1
  of adverse underlying move. The market fit says delta is 0.41. The gap between 0.41 and 0.75
  is close-based overshoot and spread, which is consistent with the comment, but the number is
  worth re-deriving from this fit rather than from 390 trades of paper history.

No engine change, no config change, no commit has been made.
