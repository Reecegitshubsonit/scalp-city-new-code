# Trade dissection, 2026-11-13 (both engines)

Market: gap-down trend day. QQQ opened 688.51, high 688.75 at 9:30, low 671.71 at 11:22, closed 679.89.
SPY 760.02 -> low 745.20 at 11:38. IWM 278.95 -> low 274.67 at 10:21. EMA9 < EMA21 on every ticker from 9:35 on.
A short-side trend day. Both engines finished net short of their losses with zero winning trades.

| Engine | Folder | Code | Trades | Day P&L |
|---|---|---|---|---|
| :8010 | ~/scalp-city | b069ec6 (V2 trail) | 3 | -1,850 |
| :8011 | ~/scalp-city-ema5 | 4d52634 (1 ATR stop / 2 ATR target) | 4 | -1,820 |

Both engines saw identical bars and fired identical signals. The only differences are sandbox fills and what the
loss cap did with them.

## Trade-by-trade

### 1. QQQ-VWAP CALL 9:32 bar (both engines)  -670 / -820
Why it fired: the "two green candles" was the failed-breakout retry rule, not a plain VWAP cross.
- 9:30 bar: high 688.75 above VWAP 687.08, close 686.25 below. VwapCross marks CALL side "failed" (wick rejection) and arms it.
- 9:31 bar: close 687.93 above VWAP 687.18. Count 1/2.
- 9:32 bar: close 688.04 above VWAP 687.33. Count 2/2 -> fire CALL. Trend filter: EMA9 687.65 > EMA21 687.53 by 0.12 (0.17 ATR; squeeze cutoff 0.15 ATR, passed by 0.02 ATR).
- Stop 687.33 (1 ATR = 0.71). 9:34 bar closed 686.40, stop hit. Option 5.67 -> 5.00 (:8010, broker_offmarket clamp) / 5.65 -> 4.83 (:8011).
What was wrong: entry 2 minutes into the session, 0.7 ATR above VWAP, EMA9/21 essentially flat, into a gap-down open. The two-closes rule confirms "price held above VWAP for two bars"; it says nothing about direction of the day. Confirmation after a wick rejection is the design, so this is a rule weakness, not a bug.

### 2. SPY-VWAP CALL 9:32 bar (both engines)  -830 / -470
Same mechanism as QQQ: 9:30 wick rejection, 9:31 and 9:32 closes above VWAP, fire. Stop 759.03. 9:34 bar closed 758.10, stop hit.
- :8011 sold 2.58 first try at 9:35 -> -470.
- :8010 SELL_CLOSE got NO_FILL at 9:35 (bid 2.59) and 9:36 (bid 2.38), filled 2.19 at 9:37 -> -830. Two minutes of unfilled sandbox exit cost 390 and tripped the engine cap by itself. Exit not filling at the bid for two bars in a 300+ contract/min market is a sandbox artefact, but the engine has no retry logic beyond "next bar".
- Consequence on :8010: SPY/IWM capped P&L -830 <= -800 -> every SPY and IWM bot locked at 9:37 for the day. IWM never traded on :8010.

### 3. QQQ-RANGE PUT 9:50 bar (both engines)  -350 / -360
- Range 9:30-9:44: 683.80 to 688.75. 9:45 bar wicked to 683.66 and closed inside -> PUT side marked failed, armed.
- 9:49 close 682.81 (1/2), 9:50 close 682.14 (2/2) -> fire PUT. Trend side agrees (EMA9 684.16 < EMA21 685.13). Stop 683.22 (1 ATR 1.08).
- 9:51 bar closed 683.26, four cents through the stop. Sold 5.46 (both engines).
- Then QQQ went 682.56, 682.59, 683.48, 681.01, 680.80, 678.14 ... 671.71. The 682P printed 6.20 at 9:55, 7.84 at 10:03, 9.79 at 10:30.
- Stop sensitivity: 1.0 ATR hit at 9:51 (and again 9:54 close 683.48). 1.5 ATR (683.76) never hit. 2.0 ATR never hit.
- After the stop, memory requires a close back INSIDE the range (above 683.80) then two closes below. QQQ never went back inside. QQQ-RANGE sat in FAILED_BREAKOUT_HOLD for the whole 16-point slide. Fix-candidate, not a bug.

### 4. IWM-RANGE PUT 9:50 bar (:8011 only)  -170
- Range 277.60 to 279.16. 9:45 wick 277.50 inside close -> failed/armed. 9:49 277.27, 9:50 277.13 -> fire PUT. Stop 277.40 (ATR 0.27).
- 9:51 bar closed 277.42, two cents through. Exit 1.39 was broker_offmarket (sandbox price outside 1.39/1.40 quote, clamped to bid). Trade did go through.
- IWM then fell to 274.67 by 10:21; the 277P printed 3.04 at 10:21. Same lock-out afterwards: never back inside range, no re-entry.

### 5. SPY-RANGE PUT: 88 signals, zero orders (:8011 only)
From 9:49 to 10:33 SPY-RANGE fired a PUT signal every single bar (range retry logic refires while beyond the level
after an unfilled entry). Every one refused with LOSS_ROOM: estimated stop loss 500-570 vs room 330 (after QQQ-VWAP
does not count; SPY-VWAP -470 left 330), then 160 after IWM-RANGE lost 170.
SPY went 755.40 -> 745.20. The 755P went 3.27 -> 7.63 by 10:20 (+4.36 x 10 x 100 = roughly +4,360 at the peak, +3,000 at 10:34 when the trend filter finally flipped).
This was the day's trade and the cap blocked it 88 times. On :8010 SPY was already fully locked so it never even signalled.

## Structural findings, ranked

1. Shared SPY/IWM loss cap turned one bad sandbox exit into a locked day. On :8010 one SPY-VWAP exit that took three bars to fill (-830 instead of -470) locked SPY and IWM at 9:37 of a 10-point SPY trend day. On :8011 the same cap, with 330 then 160 of room, refused 88 SPY-RANGE puts whose estimated risk (500-570) was based on the full 10-contract 1 ATR stop. No size-down option exists: risk check is pass/fail on 10 contracts.
2. Failed-breakout memory on RANGE requires a return INSIDE the range to re-arm. On a trend day price never returns inside, so one 1 ATR stop-out (by 4 cents on QQQ, 2 cents on IWM) ends that side for the session. The two biggest moves of the day happened while the range bots were in FAILED_BREAKOUT_HOLD.
3. 1 ATR initial stop on 1-minute ATR at 9:50 is 1.08 QQQ points on a day with 2-point bars. Both RANGE puts were stopped by less than 5 cents and both would have run 5-10 points. 1.5 ATR would have held both. This is one day; the backtest grid decides, not this day.
4. VWAP two-closes retry fires in the first 3 minutes with no regard for the open. Both VWAP calls were the identical pattern: 9:30 wick above VWAP, two closes above, long at 9:32 against a gap-down. EMA9/21 "trend" was 0.12 points apart. The squeeze filter (0.15 ATR) missed by 0.02 ATR.
5. EMA50 bots did nothing all day. Price gapped below the 5-minute EMA50 at the open and never crossed back, so no cross = no signal, on the cleanest trend day in weeks. The EMA50 trigger is cross-only; it has no "already below, confirm continuation" path.
6. Sandbox fill quality. broker_offmarket exits on QQQ-VWAP (:8010) and IWM-RANGE (:8011), two consecutive NO_FILLs on SPY-VWAP (:8010). Two engines sending orders on the same contracts in the same second (QQQ 682P x2, SPY 760C x2) may be feeding each other.

## What this day was NOT
- Not a data problem: both engines saw the same bars; 5 and 4 HTTP 429 errors were caught and retried.
- Not a side error: every entry was on the trend-filter side. Trend filter said CALL at 9:32 because the 9/21 had not yet rolled over after the gap.
- Not a lot of trades: 3 and 4 trades. The loss is 100% from entry timing (first 3 minutes) and stop width, then from being locked out of the actual move.

## Counterfactuals (this day only, not a backtest)
| Change | Effect today |
|---|---|
| No VWAP entries before 9:35 | removes -1,500 (:8010) / -1,290 (:8011) |
| RANGE stop 1.5 ATR | QQQ 682P and IWM 277P run; at 10:30 roughly +3,900 and +1,500 instead of -350 and -170 |
| Loss-cap room check sizes down instead of refusing | SPY-RANGE put at 9:50 with 5-6 contracts: +1,500 to +2,400 by 10:20 |
| RANGE re-arm without return inside | at least one re-entry on QQQ and IWM during the slide |
