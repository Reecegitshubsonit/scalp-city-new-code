# New-code entry rules (2026-11-06)

Applies to the new-code paper engine, not the regular engine.

## SIDE_RULES

- `trend` (VWAP, Range): require EMA9/EMA21 agreement with the trigger;
  otherwise skip. Never replace the trigger direction or fade it. EMA9 > EMA21
  means CALL; otherwise PUT. Missing EMAs cannot establish agreement and skip.
- `own` (5-minute EMA50): keep the trigger's direction; no trend filter or
  failed-breakout memory. The existing trading window and ATR rules are unchanged.

## Failed-breakout memory (VWAP, Range only)

Each bot tracks CALL and PUT separately for the session. A close-based stop, or
wick through the signal level followed by a close back inside/on the non-signal
side, marks that direction failed. Rejection marks a setup even if no trade filled.
A failed direction must return inside the range (VWAP: back through the current
bar's VWAP), then close strictly beyond its level twice in succession. Returning
inside/to the non-signal side resets the count. Touching the boundary is not an
outside confirmation. A rejected candle itself can re-arm the next attempt.

For Range, this second-close rule deliberately bypasses the old previous-close-
inside condition: the previous close on confirmation is already outside. The
confirmation consumes its arm so staying outside cannot signal repeatedly.
An unfailed side retains its original single-close/cross signal rule.

A full target exit clears that side's failure; a new session clears both sides.
Stops still inspect bar.close, never a wick. Cooldown and all risk/size/ATR
settings are unchanged. `TREND_FILTER_SKIP` and `FAILED_BREAKOUT_HOLD` explain
blocked entries in the event log/dashboard.

## Recorded IWM regression

`tests/fixtures/iwm-2026-11-06-opening.json` copies the new-code IWM OHLCV tape
and per-bar logged indicators. Opening range: 270.24–272.11. Times below are MST.
The original first entry is 07:46 and close-based stop is 07:55. The 08:00 bar
(former entry at 08:01) is now blocked. The 08:09 and 08:10 bars supply the two
held closes, allowing an entry at 08:11. This checks entry eligibility, not the
option P&L obtainable at that delayed entry.
