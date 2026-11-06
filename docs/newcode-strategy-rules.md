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

## Session window, sizing and loss cap (2026-11-06 afternoon)

### No new entries from 11:00 ET (every bot)

All session times are US/Eastern bar end times (`bar.end` converted to
America/New_York explicitly). `Settings.last_entry = 10:59` and
`Settings.no_entry_from = 11:00`: the last possible entry is on the bar ending
10:59; nothing opens at or after 11:00:00 ET (reason `OUTSIDE_WINDOW`, "no new
entries from 11:00 ET"). A trade already open is NOT closed at 11:00: it runs to
its 1-ATR stop or 2-ATR target (bar.close), or the 15:55 ET end-of-day flatten
(`Settings.flat_by = 15:55`, `EXIT_TIME`) if still open then.

### 5-minute EMA50 contracts

VWAP and Range trade 10 contracts. EMA50 stops on the 5-minute ATR, so its size
is shrunk so a 1-ATR stop risks about what a 10-contract 1-minute ATR stop does:
`qty = max(1, min(10, round(10 * atr_1m / atr_5m)))` (half rounds up), with the
symbol's 1-minute ATR(14). If the 1-minute ATR is unavailable, qty = 4
(`Settings.ema50_fallback_contracts`). Example: atr_5m = 2.5 x atr_1m -> 4.
Stop/target stay 1 ATR / 2 ATR (5-minute ATR), checked on bar.close.

### Engine-wide daily loss cap

`--daily-loss 800` (and `Settings.daily_loss`, default now 800) is ONE cap for
the whole engine, not $800 per bot.

- Engine P&L = sum of every bot's realized day P&L (entry fees included).
- Remaining room = daily_loss + engine P&L (down $600 -> $200 room).
- Before an entry: estimated stop loss = |entry - 1-ATR stop| (underlying $)
  x 0.75 (`Settings.risk_per_und_dollar`) x qty x 100, capped at the premium
  paid at the ask. The entry is refused if that exceeds the room
  (`LOSS_ROOM`), if room is <= 0 (`ENGINE_DAILY_LOSS`), or if the risk cannot be
  estimated (`RISK_UNKNOWN`). 0.75 is the median realized loss per $1 of stop
  distance per contract over 390 losing Webull paper trades (it includes
  close-based overshoot and spread); ATM delta alone would be 0.5.
- After any completed trade (and after a restart), if engine P&L <= -800 every
  bot is locked for the day (`ENGINE_DAILY_LOSS`). A bot still holding keeps
  being managed to its stop/target/15:55 exit; nothing new opens.
- Unchanged: the per-bot $600 goal lock, and a bot whose own P&L reaches -800
  still locks itself (`DAILY_LOSS`, stricter than the engine cap, never looser).
