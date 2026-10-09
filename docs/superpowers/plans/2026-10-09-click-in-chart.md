# Click-in chart and room: plan

Approved by the user 2026-10-09: engine `/history` with full candles; view click-in with a live chart and a 3D room
with three wall charts and the scanner. Not in this round: tower mini-billboards, past-day replay, room dressing.

## Engine (additive, new files plus two small wirings; other uncommitted engine edits are untouched)
1. `scalpcity/history.py`: `BarStore` (thread-safe today's bars per ticker) and `build_history(ticker, bars, events)` returning
   `{ticker, bars:[{time,open,high,low,close,volume}], levels:[{time,vwap,ema9,ema21,ema50}], marks:[{time,bot,type,side,pnl}]}`.
   Marks come from the event log (ENTRY_FILL = entry, trade_closed = exit); side from the bot's SIGNAL text.
2. `scalpcity/server.py`: optional `history_fn`; `GET /history?ticker=QQQ` (404 unknown ticker or no store).
3. `scripts/run_live.py`: fill the store from `feed.startup` and every `feed.poll` bar, pass `history_fn`.
4. pytest first; restart the engine afterwards (user approved).

## View
5. Mock: same `/history` endpoint (synthetic candles).
6. Model: history types, merge live ticks into the candle series, chart header text (pure, tested).
7. Candle chart component: header "QQQ . Fri 10/9 . 12:40 . 750.46 +0.53% . 9 trades", candles, VWAP/EMA lines, labelled markers, live updates.
8. Click-in: camera flies in, floating in-scene chart beside the tower, room overlay shows the chart large.
9. Room: three wall charts (SPY, QQQ, IWM, 1-MIN), scanner, heatmap, leaderboard, market plaque, EARNED card.
10. Verify against the real engine, 60 fps, update README.
