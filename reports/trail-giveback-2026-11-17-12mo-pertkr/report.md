# Exit grid re-run with measured per-ticker costs

Run 2026-11-17. Script `backtest/trail_grid.py`, raw output `results.csv` / `results.json`.
Data: SPY/QQQ/IWM 1-minute bars, 2025-11-17 to 2026-11-13, 250 trading days, live 10:59 entry
cutoff. Entries fixed; only the exit varies.

Costs are no longer a single pooled guess. They come from
`reports/premium-fit-2026-11-17/report.md`: measured Webull spreads divided by the option-bar
delta fit times each ticker's median 1-minute ATR.

| Ticker | COST_R |
|---|---:|
| QQQ | 0.094 |
| SPY | 0.079 |
| IWM | 0.313 |

## 1. Nothing in the grid is profitable after measured cost

Every one of the 38 exit configurations is negative after per-ticker cost. The best cell in the
whole run is `giveback stop1 arm0.5 give0.75` on QQQ+SPY at **+0.006 R, t = +0.14** — which is
zero.

| Exit | Trades | avgR | after pooled 0.2 | after per-ticker | t |
|---|---:|---:|---:|---:|---:|
| `stop_target 1.0/2.0` (new bot today) | 5859 | −0.003 | −0.203 | −0.163 | −8.80 |
| `live_v2 trail1.5 arm0.5` (V2 today) | 6150 | +0.008 | −0.192 | −0.153 | −7.39 |
| `giveback stop1 arm0.5 give0.5` | 6585 | +0.041 | −0.159 | −0.119 | −5.49 |
| `giveback stop1 arm0.5 give0.75` | 6297 | +0.106 | −0.094 | −0.054 | −1.62 |
| `giveback stop1 arm4 give0.75` | 5063 | +0.107 | −0.093 | −0.054 | −1.07 |

Per-ticker costing is *kinder* than the flat 0.2 (−0.153 against −0.192 for the live exit),
because two of three tickers are cheaper than 0.2. It does not rescue anything.

**This says the problem is not the exit.** The looser-trail finding still holds in raw R — the
monotone give-pattern survives — but no exit shape in the grid produces entries that clear the
spread. That is an entry-quality result, and it is the first time the grid has been able to
say so, because a pooled constant was masking which tickers paid what.

## 2. IWM has the best raw edge and the worst net result

| Exit | Ticker | n | raw avgR | after cost | t |
|---|---|---:|---:|---:|---:|
| `live_v2` | SPY | 2083 | +0.019 | −0.060 | −1.71 |
| | QQQ | 2049 | −0.026 | −0.120 | −3.43 |
| | **IWM** | 2018 | **+0.031** | **−0.282** | −7.61 |
| `giveback give0.5` | SPY | 2235 | +0.008 | −0.071 | −2.58 |
| | QQQ | 2204 | +0.008 | −0.086 | −2.58 |
| | **IWM** | 2146 | **+0.109** | **−0.204** | −4.11 |
| `giveback give0.75` | **SPY** | 2133 | **+0.140** | **+0.061** | +1.05 |
| | QQQ | 2113 | +0.044 | −0.050 | −0.92 |
| | IWM | 2051 | +0.136 | −0.177 | −2.96 |

IWM posts the highest raw expectancy of the three on the current live exit (+0.031 against
QQQ's −0.026) and the worst after-cost by a wide margin. The signals on IWM are not bad. The
instrument is unaffordable at our size: 0.313 R of spread per round trip against a 1-minute
ATR of 0.174 points.

Dropping IWM improves every configuration in the grid. On the live exit, −0.153 pooled becomes
−0.090 for QQQ+SPY.

## 3. QQQ-only is the wrong cut

The suggestion was to follow Nick Fischer, who began on QQQ/SPY/IWM and now trades QQQ alone.
Our data says the opposite, and says it consistently:

| Exit | QQQ only | QQQ + SPY |
|---|---:|---:|
| `stop_target 1.0/2.0` | −0.101 | −0.092 |
| `live_v2` | −0.120 | −0.090 |
| `giveback give0.5` | −0.086 | −0.078 |
| `giveback give0.75` | −0.050 | **+0.006** |
| `giveback stop1 arm4 give0.75` | −0.065 | −0.006 |

QQQ is the weakest of the three tickers on raw expectancy in four of the five exits shown, and
it is not the cheapest — SPY is, at 0.079. Every cell improves when SPY is kept. The only
after-cost positive anywhere in the run is **SPY on `give0.75`: +0.061 R, t = +1.05** — not
significant, but it is the single best thing in the grid, and QQQ-only discards it.

His instrument choice is evidence about his system, not ours. He holds for a median of 103
seconds on five bots sized up to 160 contracts, entering on rules we have not reproduced.
Nothing about that transfers to a 10-contract engine holding 4–5 minutes on different signals.
What his migration does corroborate is the narrower claim already in the cost report: a cheap,
high-ATR instrument beats an expensive, low-ATR one. For us that argues against IWM. It does
not argue for QQQ over SPY.

## 4. Caveats

- Underlying-price model. No option convexity; the premium response is the linear delta fit.
- Hard stops fill exactly at the stop price intrabar, which flatters tight stops.
- 38 configurations per entry set; treat single t-statistics accordingly.
- Costs are spread only. No commissions, no slippage beyond the spread, no partial fills. Real
  costs are higher, so these after-cost figures remain optimistic.
- No daily loss cap, goal lock, loss-room check or profit brake. The 2026-11-13 dissection
  shows the shared SPY/IWM cap can dominate a day, and none of that is modelled.

## 5. What this points at

1. **Drop IWM**, pending the same test on the option replay. It is the clearest result here:
   good signals, unaffordable spread, worst net on every configuration.
2. **Keep SPY.** It is the cheapest ticker and carries what edge exists.
3. **The exit is not the bottleneck.** Entries do not clear the spread on any exit shape
   tested. Further exit tuning is polishing the wrong thing.

No engine change, no config change, no commit has been made.
