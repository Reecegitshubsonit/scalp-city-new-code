# Edge hunt, 2026-11-06

Sources: `logs/*-live.jsonl` and recorded Webull bars. 19 full paper days for logged signals (2026-10-09 to 2026-11-05),
573 closed trades, -$16,140. Today (2026-11-06) is excluded: 26 trades, -$7,820 when this ran at about 15:39 ET.
Scripts: `analyze.py` (`results.txt`, `signals.csv`), `second_pass.py` (`second_pass.txt`), `third_pass.py` (`third_pass.txt`).

Stock-only metric: target% is how often closes reach +2 ATR before -1 ATR, flat at 15:55. It ignores option costs.

## Bug: session VWAP includes the prior day's closing bars

`LiveFeed.poll` (`scalpcity/live.py`) has no `last_ts` for a ticker when the engine starts before the open. Its first poll
therefore emits every bar returned by `recent_bars(t, 3)`, including the prior session's last bars. `Engine.on_bar` feeds them
into `IndicatorSet.update`, so they enter today's VWAP. The 15:59 bar has very large volume, so the distortion lasts for hours.

- The logged 09:31 VWAP is reproduced within 2 cents by adding prior-session bars on 52 of 54 ticker-days (2 bars: 42, 1 bar: 10).
- Example, QQQ 2026-11-05: logged 689.22; the 09:30 bar alone gives 682.003; with the prior two bars, 689.220.
- Of 144 logged VWAP signals, 107 used a level more than 0.25 ATR from true VWAP, 31 had price on the wrong side of true VWAP,
  and only 48 were true crosses on that bar. Mean error: 1.40 ATR.
- The prior bars also set `prev_close`, so the first bar can fire a cross across the overnight gap. Without them it could not fire.
  09:31 signals produced 43 closed trades, -$3,130, 15 wins, and $20,670 of absolute P&L. The two largest wins and two largest
  losses through 11-06 are in this group (QQQ-VWAP and QQQ-EMA50 on 10-29 and 10-30).
- EMA and ATR also see those bars a second time, a smaller effect. RANGE levels are unaffected.

Not fixed in this report. `tests/test_live_broker.py` currently expects the first poll to emit recent bars.

## Results

Placebo, any minute 09:45-15:30: random side target 37.5%; EMA9/21 side target 38.5%.
All logged signals, side as traded: target 37.5%.

True session VWAP from recorded bars, 908 crosses over 20 days (`third_pass.txt`):

| Rule | Target % | r30 (ATR) |
|---|---:|---:|
| Trade with the cross | 35.0 | -0.09 |
| Fade the cross | 37.0 | +0.09 |
| EMA9/21 side | 36.2 | +0.10 |

ORB first break only, one per ticker-day: 60 signals, 33.3% target (early 23.3, late 43.3).
ORB failed break, fade back in: 43 signals, 39.5% target (early 50.0, late 26.3).

Actual option results, side compared with the cross direction:

| Group | Trades | P&L | Early P&L | Late P&L |
|---|---:|---:|---:|---:|
| With cross | 365 | -$17,190 | -$8,470 | -$8,720 |
| Against cross | 208 | +$1,050 | +$7,950 | -$6,900 |

The early with-cross group includes 2026-10-09, which ran before `trend_side`. The difference does not appear in the late half.

Other slices (`results.txt`):
- RANGE break under 0.5 ATR past the edge: 117 signals, target 43.6% (early 43.1, late 43.9), +$2,780, day-clustered t +2.64.
- RANGE break of 0.5 ATR or more: 47 signals, target 31.9%, -$5,380.
- RANGE trades against the break: 30 trades, +$3,330, target 58.3%; late half -$130.
- Up breaks +$3,830, down breaks -$3,560; late-half up breaks -$1,690. May reflect the market's direction.
- 11:30-13:59 logged signals: r30 -0.48, t -2.00, -$6,330. Rebuilt VWAP crosses do not show the same effect.

Caveats: about 60 slices were examined, so a few |t| > 2 are expected by chance. Trades within a day are correlated.
Logged VWAP-side groupings use the contaminated level. Nothing here was tested on held-out days.

## Actual exits

| Half | Trades | P&L | Win % | Avg win | Avg loss | Mean ATR |
|---|---:|---:|---:|---:|---:|---:|
| Early | 274 | -$520 | 38.7 | $317 | -$203 | 0.296 |
| Late | 299 | -$15,620 | 35.5 | $369 | -$283 | 0.358 |

Stop exits averaged -1.55 and -1.49 ATR of stock move; target exits +2.29 and +2.42. The cause of the wider dollar losses in the
late half is not established. Entry spread cost is about 9% of a 1 ATR option move on QQQ and SPY and 25% on IWM, assuming 0.5 delta.
