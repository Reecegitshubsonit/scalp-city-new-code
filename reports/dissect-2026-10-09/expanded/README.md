# Expanded trade data: Scalp City paper session, Friday 2026-10-09

Built only from `logs/2026-10-09-live.jsonl` by `build.py` (read-only; rerun with `python3 reports/dissect-2026-10-09/expanded/build.py` from the repo root).
Nothing here was sent to the broker and nothing in the bot was changed.

**Scope.** The 52 closed trades, numbered exactly as in the original table (`../signal_table.csv`, left unchanged; `n` and P&L match row for row).
The three positions left open by the 09:58-10:00 restart (SPY-VWAP PUT 09:43, QQQ-EMA50 PUT 09:55, QQQ-RANGE PUT 09:55) are excluded from every file and from the overlap check.

## Files

| file | rows | what it holds |
|---|---|---|
| `trades_expanded.csv` | 52 | one row per trade, 61 columns (below) |
| `price_paths.csv` | 622 | the underlying's 1-minute path for each trade, signal minute to exit-fill minute, in order |
| `orders_issues.csv` | 11 | 4 entries that did not fill, 1 entry with no logged outcome, 6 exit retries |
| `settings_used.csv` | 15 | strategy settings in force that day, the log evidence, and how sure each one is |

## trades_expanded.csv columns

**Identity**
- `trade_id`: `date-bot-HHMM` of the entry fill. Unique.
- `n`: row number in the original 52-trade table.
- `bot`, `ticker`, `trigger` (VWAP, EMA50 or RANGE), `side` (CALL or PUT).
- `option_symbol`: OCC symbol as sent to Webull. `expiration`, `strike`: decoded from it.
- `qty_ordered`, `qty_filled_entry`, `qty_filled_exit`: contracts. All 10; no partial fills were logged.

**Signal**
- `signal_time`, `signal_seq`: the bar that fired, and its log sequence number.
- `signal_und_close`: underlying close on that bar. Stop and target are measured from it.
- `atr_at_signal`, `charge_pct_at_signal`.
- `vwap_at_signal`, `ema9_at_signal`, `ema21_at_signal`, `ema50_at_signal`: indicator values the bot saw.

**Risk levels (underlying price)**
- `stop_und_logged`, `target_und_logged`: as written by the bot in its "held, stop X, target Y" lines. Missing for #5, 21, 30, 41, 48 (exit came before a holding line was written).
- `stop_und_reconstructed`, `target_und_reconstructed`: signal close ∓ 1 ATR and ± 2 ATR. Equal to the logged values on all 47 trades that have both.

**Entry**
- `entry_order_time`, `entry_order_seq`: when the buy order was sent.
- `entry_bid`, `entry_ask`: option quote at order submission (from the order line).
- `entry_fill_time`, `entry_fill_seq`, `entry_fill_price`.
- `entry_fill_source`: `broker` = Webull sandbox fill; `broker_offmarket` = sandbox price was outside the quote and was re-booked at the quote.
- `entry_fill_in_quote`: whether the fill price is within the bid/ask, allowing 1 cent.
- `und_at_entry_fill`: underlying close on the fill bar.

**Exit**
- `exit_trigger` (STOP or TARGET), `exit_trigger_time`, `exit_trigger_und_close`: the bar close that tripped the exit.
- `exit_orders_sent`, `exit_retries`, `exit_retry_times`: sell orders sent and how many failed to fill first.
- `exit_order_time`, `exit_bid`, `exit_ask`: the final sell order and its quote.
- `exit_fill_time`, `exit_fill_seq`, `exit_fill_price`, `exit_fill_source`, `exit_fill_in_quote`: as for the entry.
- `und_at_exit_fill`.
- `exit_R_und`: underlying move from the signal close to the exit fill, in signal ATR, signed so + is in the trade's favour. −1 = exactly at the stop line.

**Result**
- `hold_min`: entry fill to exit fill, in minutes.
- `pnl_logged`: the bot's P&L.
- `pnl_at_mids`: the same trade priced at quote mids. Use this where the fill was off-market.
- `bot_pnl_day_after`, `bot_trade_count_after`: the bot's running totals after this trade.
- `close_state`: COOLDOWN, or DAILY_LOSS if this trade locked the bot.
- `fee_logged`: empty for every trade. Fees were not recorded.

**Overlaps and flags**
- `opposing_overlap`: other bots holding the **opposite** side on the same ticker at the same time (open interval, entry fill to exit fill). Unintended.
- `same_side_overlap`: other bots holding the same side at the same time (doubled exposure).
- `flags`: every known caveat for the row, separated by `|`.

## price_paths.csv columns
- `trade_id`, `n`, `minute`.
- `phase`: signal, holding, exit trigger, or exit fill.
- `und_close`, `vwap`, `ema9`, `ema21`, `ema50`, `atr`: what the bot saw that minute.
- `move_R`: close minus signal close, in signal ATR, + = trade's favour.
- `dist_to_stop_R`, `dist_to_target_R`: room left to each level, in R (0 = at the level).

Minutes with no bar (feed gaps, restart) have no row. That's how the 11:09-11:16 gap shows up.

## Missing or uncertain fields

| field | status |
|---|---|
| All timestamps | **Bar-end minutes, not execution wall-clock.** The log stamps orders and fills with the bar's end time, so real fill latency can't be measured. |
| Limit prices | **Not logged.** The code places buys at the ask and sells at the bid; treat them as equal to `entry_ask` and `exit_bid`. |
| Bid/ask on fill records | Only present from 11:27 (exits) and 11:32 (entries). Earlier rows use the quote on the order line, sent the same minute. |
| Stop/target, 5 trades | Not in the log text; the reconstructed values are used (they matched exactly on the other 47). |
| Fees | Not logged (`fee` is empty on all 107 fills). |
| Fill prices #2, #4, #5 | Sandbox printed prices outside the quote before the off-market check existed. `pnl_logged` overstates these three by $1,035 combined; use `pnl_at_mids`. |
| #7, #8 | Sandbox prices outside the quote were re-booked at the quote; the broker account holds different prices than the log. |
| Daily loss/goal limits | Not logged as values; inferred ranges are in `settings_used.csv`. Different before and after the restart. |
| Code version | The run used an uncommitted working tree; the exact version isn't recorded. A second restart around 11:09-11:16 is likely (fill records gain quote fields afterwards) but not logged. |

## Findings from the expanded data
- **Opposing overlaps: 16 trades in 8 groups** held a CALL and a PUT on the same ticker at once (#1/#6, #9/#14, #16/#18, #23/#24/#28, #29/#30, #37/#39/#40/#42/#45). Combined: −$210 logged, −$105 at mids. **Each bot manages only its own position**; nothing stops two bots on one ticker from taking opposite sides.
- **Same-side overlaps: 18 trades** doubled exposure on one idea (e.g. #7/#8, #12/#13, #15/#16, #19/#20).
- **Entry order with no outcome:** QQQ-RANGE sent a buy for QQQ261012P00749000 at 10:12 (seq 403) and logged neither a fill nor a failure. QQQ-EMA50 tried the same contract the same minute and logged NO_FILL. This is the likely source of the 10 extra QQQ 749 puts in the broker account (unconfirmed until checked against Webull's order history).
- **Exit retries: 6.** In #29 (QQQ-VWAP, 11:58) the retry fired on the TARGET exit, and the trade later stopped out.
- **Fill quality:** 49 of 52 trades filled inside the quote (within 1 cent). Total P&L −$2,270 logged, **−$3,130 at quote mids**.
