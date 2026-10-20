# Range bots that become trend bots after the first range trade (run 2026-10-20, 10:35 ET)

Question: if each range bot took its normal opening-range break, then switched to a trend rule for the rest of
the day, what would the Webull paper days have looked like?

Days: 2026-10-12, 13, 14, 15, 16, 20. 10-19 is skipped (the engine did not run, DNS failure). 10-20 covers
bars up to 10:35 ET only. Script: `sim.py`. Outputs: `results.txt`, `trades.csv`, `logs/<variant>/`.

Everything except the trigger is the live engine: 10 contracts, 1 ATR stop, 2 ATR target, 2 min cooldown,
side from EMA9 vs EMA21, $600 daily goal and $800 daily loss per bot, last entry 15:30 ET, flat by 15:55 ET.

Trend rules tried after the first range signal:
- `pullback`: a bar's wick reaches EMA9 and the bar closes back on the trend side.
- `reenter`: enter again in the EMA9/EMA21 direction as soon as cooldown ends.
- `cross`: enter when EMA9 crosses EMA21.

## Results (range bots only, dollars)

| variant  | trades | total | per trade | trades after the first range trade | their P&L |
|----------|-------:|------:|----------:|-----------------------------------:|----------:|
| range    |     48 | -1510 |     -31.5 |                                 30 |     -2060 |
| pullback |    175 | +2510 |     +14.3 |                                157 |     +1960 |
| reenter  |    196 |  -890 |      -4.5 |                                178 |     -1440 |
| cross    |     99 |  +590 |      +6.0 |                                 81 |       +40 |

- Pullback is the only rule with a positive total. It is positive on 4 of 6 days. It loses -1860 (10-12)
  and -1990 (10-13), and both of those days are priced from candles.
- On the four days priced from real bid/ask (10-14 to 10-20), pullback is +6360 and range is -540.
- Pullback's per-trade edge is small: +14.3 per trade on 10 contracts, about $0.014 per contract.
  A slightly worse fill would remove it.
- Reenter takes the most trades and loses. IWM-RANGE alone takes 142 trades with it.
- Today on SPY, pullback adds one trade: 10:06 to 10:14, +590, after the +410 range trade. That puts SPY-RANGE
  over the $600 daily goal, so it locks for the day. QQQ-RANGE locks after its first trade (+1040).

## Caveats

- The daily goal and loss locks shape the results. In the pullback run, bots locked on the goal 8 times and
  on the loss 4 times. A winning first trade of $600 or more means the trend rule never trades that day.
- Replay fidelity: the replayed `range` bot does not match the real live P&L (real: 10-12 +530, 10-13 -910,
  10-14 +1450, 10-15 -960, 10-16 -1660, 10-20 morning +1770). Compare the variants with each other, not with
  the real account.
- 10-12 and 10-13 have no bid/ask snapshots. They use Webull option candle closes +/- half-spread, and only
  for the few strikes that were saved. Pullback had 42 refused orders and reenter 28 for missing quotes there.
- On snapshot days, contracts that left the recorded strike ladder fall back to candles (listed in
  `results.txt`). Without that, 10-14 positions could not exit for hours.
- Six days, one market regime. 10-20 is a strong up day and only partly covered.
