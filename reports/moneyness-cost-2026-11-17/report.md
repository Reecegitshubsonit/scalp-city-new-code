# Does buying in the money lower the cost hurdle? No.

Run 2026-11-17. Script `backtest/moneyness_cost.py`, raw output `results.json`.
Source: `data/webull/<day>/` — snapshot quotes and 1-minute option bars across roughly +/-10
strikes on every paper day, against 1-minute stock bars.

`COST_R = quoted spread / (realised premium response per 1 ATR)`. Moving in the money raises
delta, which should lower the hurdle. It can also widen the spread, which raises it. Both sides
measured on the same contracts the engine could have bought. Moneyness is signed so positive
is in the money, in dollars.

## Result

| QQQ bucket | Spread | \|delta\| | delta_eff | $/ATR | **COST_R** |
|---|---:|---:|---:|---:|---:|
| < −2.5 OTM | 0.0200 | 0.466 | 0.242 | 0.094 | 0.214 |
| −1.5..−0.5 | 0.0200 | 0.478 | 0.448 | 0.173 | 0.115 |
| **ATM ±0.5** | 0.0200 | 0.500 | 0.480 | 0.186 | **0.107** |
| +0.5..+1.5 | 0.0200 | 0.522 | 0.495 | 0.192 | **0.104** |
| +1.5..+2.5 | 0.0200 | 0.539 | 0.496 | 0.192 | **0.104** |
| +2.5..+3.5 | **0.0300** | 0.538 | 0.504 | 0.195 | 0.154 |
| > +3.5 ITM | **0.0300** | 0.533 | 0.568 | 0.220 | 0.136 |

| SPY bucket | Spread | delta_eff | **COST_R** | | IWM bucket | Spread | delta_eff | **COST_R** |
|---|---:|---:|---:|---|---|---:|---:|---:|
| < −2.5 OTM | 0.0100 | 0.211 | 0.169 | | < −2.5 OTM | 0.0100 | 0.132 | 0.596 |
| −1.5..−0.5 | 0.0100 | 0.442 | 0.080 | | −1.5..−0.5 | 0.0100 | 0.351 | 0.224 |
| **ATM ±0.5** | 0.0100 | 0.485 | **0.073** | | **ATM ±0.5** | 0.0200 | 0.442 | 0.356 |
| +0.5..+1.5 | **0.0200** | 0.517 | 0.137 | | +0.5..+1.5 | 0.0200 | 0.506 | 0.311 |
| +1.5..+2.5 | **0.0200** | 0.528 | 0.134 | | +1.5..+2.5 | **0.0300** | 0.566 | 0.418 |
| > +3.5 ITM | 0.0200 | 0.635 | 0.112 | | > +3.5 ITM | 0.0300 | 0.693 | 0.341 |

## Verdict, and a correction

**ITM does not help, and on SPY it roughly doubles the cost.**

- **SPY**: ATM is the cheapest cell in the entire study at **0.073 R**. One strike in the money
  the quoted spread goes 0.010 to 0.020 and the hurdle goes to 0.137 — the spread widening
  swamps the delta gain.
- **QQQ**: ATM 0.107 against 0.104 one or two strikes in. A 3% improvement, inside noise. Past
  +2.5 the spread widens to 0.030 and the hurdle rises to 0.154.
- **IWM**: ATM 0.356, worse at every ITM bucket, 0.418 at +1.5..+2.5.

**Correction.** I estimated this change would cut the QQQ hurdle 37%, from 0.094 to 0.059,
assuming delta ~0.65 at $2 in the money. That was wrong. Measured realised `delta_eff` at
+1.5..+2.5 on QQQ is **0.496**, not 0.65, and quoted delta is 0.539.

The reason is scale. $2 in the money on a $660 underlying is 0.3% — barely in the money in
percentage terms, so delta stays near 0.5. Nick Fischer's "$2 ITM" rule is, on QQQ, almost
exactly at the money. On IWM at ~$270, $2 is 0.74% and delta does reach 0.684 — but IWM's
spread widens to 0.030 there and the hurdle gets worse anyway.

## What the table does confirm

**Out of the money is expensive.** QQQ 0.214, SPY 0.169, IWM 0.596 in the far-OTM bucket,
against 0.107 / 0.073 / 0.356 at the money. Realised `delta_eff` collapses to 0.13–0.24 while
the spread stays the same. `atm_strike()` is already close to the best available choice on all
three tickers.

**SPY at the money is the cheapest instrument we have**, at 0.073 R. That is the third
independent result today pointing at SPY over QQQ.

**The earlier per-ticker costs stand**, derived differently: 0.094 / 0.079 / 0.313 from pooled
spreads and a pooled delta fit, against 0.107 / 0.073 / 0.356 here from ATM-bucket spreads and
a per-bucket delta fit. Close enough to treat as the same measurement.

## Caveat

This prices the hurdle, not the outcome. Nothing here changes the finding that entry signals
show symmetric excursions; a cheaper strike makes losing slower, as a 0.073 R hurdle on a
zero-edge signal still loses.

No engine change, no config change, no commit has been made.
