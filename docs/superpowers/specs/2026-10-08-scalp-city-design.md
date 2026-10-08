# Scalp City: design spec

Date: 2026-10-08. Status: awaiting user review. Paper/sandbox only.

## 1. Goal

Run nine paper-trading bots on QQQ, SPY and IWM 1DTE options and make every bot's activity visible
and checkable: at any moment you can see what each bot is doing, how close it is to firing, and,
when it is quiet, exactly why. A 3D "city" gives the at-a-glance view; text panels give exact
numbers and reasons. The goal is trust through visibility, not a claim of profit.

Non-goals (v1): live trading, real money, the Claw3D office scene, a flatten button, stock bots,
spreads or multi-leg options, strategy optimisation.

## 2. Decisions made (with the user)

| Topic | Decision |
|---|---|
| Agents | New bots, not the existing MarketScanners scanners. Nothing in MarketScanners or trading-agents-tauric is read, used or changed |
| Trading | Long ATM 1DTE single-leg options (call on bullish trigger, put on bearish) on QQQ, SPY, IWM |
| Roster | 9 bots: triggers VWAP-cross, EMA50-cross, 15-min range break, one bot each per ticker |
| Triggers | Candle closes across VWAP / across the 50 EMA / outside the first-15-minute range. 9/21 EMA squeeze skips chop. ATR-based exits |
| Data and orders | Webull primary (live data, paper orders). Alpaca for replay history and as backup. Massive optional, unused in v1 |
| Architecture | Python engine and append-only event log are ours. Own web 3D view (React + react-three-fiber). Claw3D can be added later as one more view through an adapter. The event stream is the only contract |
| Dashboard | 3D city from the start, plus HTML panels for exact numbers |
| Log | One event-log file per trading day |
| Limits | Separate daily goal and loss limit per bot |
| Replay | Included in v1: a past day runs through the same engine and dashboard as live |
| Pause | Per-bot Pause button (no new entries; open position still managed to a normal exit) |
| Account | Webull sandbox Individual Cash paper account, selected by WEBULL_PAPER_ACCOUNT_NUMBER |

## 3. Defaults (adjustable settings, not code)

- Size: 10 contracts per trade (user choice). Daily goal +$600 and daily loss limit -$100 per bot (user choice).
  Limits are lockout thresholds checked after each closed trade, not per-trade stops, so a single trade can
  overshoot them; the user accepts overshoot in the learning stage. Both numbers are settings.
- Cooldown 2 minutes after each trade (user choice). The reference video says the bots wait after each trade but
  gives no duration.
- Trading window 9:45-15:30 ET. One open position per bot.
- Stale rule: no new bar for 2 minutes (idle bots); no fresh option quote for 30 seconds while in a trade; flatten the paper position after 5 minutes stale.
- Replay half-spread per side: SPY $0.01, QQQ $0.015, IWM $0.02.
- Order type: limit just above the ask for buys; marketable limit below the bid for sells.

## 4. Architecture

```
Feed (Webull live | Alpaca replay) -> bar and quote events
   -> Bot x9 (pure state machines) -> order intents
   -> Risk gate -> Broker (paper, Webull sandbox) -> fills
   -> every step appended to the Event log (one file per day)
Event log -> API server (WebSocket + snapshot + pause endpoint) -> Web view (3D city + panels)
```

Rules: bots hold no network or broker code. The risk gate is the only path to the broker. The view
reads events only and cannot change what a bot did. Live and replay produce identical event shapes.

## 5. Bot state machine

States: `idle` (always with a reason code), `forming` (with charge %), `fired`, `managing`,
`exiting`, `cooldown`, `locked` (daily goal or loss limit), `paused`, `stale`.
Reason codes include: OUTSIDE_WINDOW, CHOP_SQUEEZE, COOLDOWN, DAILY_GOAL, DAILY_LOSS, NO_DATA,
RANGE_FORMING, PAUSED, STALE_DATA. Charge % is the distance to the trigger in ATR units mapped to 0-100.

## 6. Event format

JSON line per event: `seq`, `time`, `mode` (live|replay), `bot`, `ticker`, `kind` (state_change,
order_sent, fill, limit_hit, feed_stale, control), `state`, `reason_code`, `reason_text`,
`inputs` (price, VWAP, EMA50, EMA9, EMA21, ATR, distance in ATR), `charge_pct`, and for orders
`contract`, `qty`, `limit`, `fill_price`, `fill_source` (broker|modeled). Files are append-only.
A snapshot (current state of each bot) is derived from the log; on page load the server sends
the snapshot, then streams new events.

## 7. Feeds and orders (verified 2026-10-08 against the Webull sandbox)

- SDK: `webull-openapi-python-sdk` 3.0.2, requires Python 3.8-3.11; project uses a local `.venv` on 3.11.
- Host: `api.sandbox.webull.com` (US sandbox). Sandbox and production keys are separate.
- Keys: app key is 35 characters (2-character prefix, dot, 32 hex); app secret is 32 hex.
- Bars: `market_data.get_history_bar` (M1, count up to 1200, start/end supported for stocks).
- Options: contract names use standard OCC format (e.g. `SPY261009C00774000`);
  `option_market_data.get_option_snapshot` (up to 20 symbols) returns bid, ask, sizes, `imp_vol`,
  greeks, `last_trade_time`, `quote_time`, `delay_minutes` (observed 0 = real-time);
  `get_option_history_bars` returns the latest N bars (max 1200).
- Orders: `order_v2.preview_option`, `place_option`, `get_order_detail`, `cancel_option`; stocks via
  `preview_order`, `place_order`, `cancel_order_v2`. ETF order place, 30-second rest and cancel
  verified. Option preview verified (HTTP 200). Option placement NOT yet verified (market closed).
- Rate limit: 300 HTTP requests per 60 seconds.
- Sandbox lists five accounts; the Individual Cash account matching the saved number is used.
- Observed 1DTE ATM spreads: $0.01-$0.04 (about 1-3% of premium); IWM puts widest.
- Cash-account caveat: a real cash account trades only settled funds; option proceeds settle next
  day. The engine tracks cash per bot so the design does not depend on sandbox leniency.

## 8. Safety

- Paper only. Startup refuses unless `WEBULL_ENV=sandbox`, `WEBULL_SANDBOX_ACCOUNT_ATTESTED=true`,
  host is the sandbox host, and the account matches `WEBULL_PAPER_ACCOUNT_NUMBER`.
- No production hostname appears in any code path that can send orders.
- Keys live in `.env` (mode 600, git-ignored). The engine reads environment variables; keys are
  never logged or placed in events.
- The engine never calls account endpoints beyond list/balance/orders of the selected account.

## 9. Dashboard

3D city: 3 districts (QQQ, SPY, IWM) with 3 towers each. Idle dim; forming beam rising with charge %
(green call, red put); fired ring flash; managing steady glow with P&L label; cooldown/locked
blue/amber; stale flickering red; paused hatched. Centre dome shows total day P&L. Orbit camera;
clicking a tower selects the bot.
Panels (HTML): 9 agent cards (state, reason, charge, P&L, Pause), thoughts feed (log tail),
leaderboard and heatmap, market and data-freshness clocks, detail drawer with the exact inputs of
the last decision.
Stack: Vite, React, react-three-fiber with bloom for glow; server FastAPI (WebSocket, snapshot, pause).

## 10. Build phases and testing

| Phase | Scope | Proof |
|---|---|---|
| 0 | Market-open checks: option place/cancel, quote freshness at 10:00 ET | Printed results |
| 1 | Event log, bot state machines, replay feed | Test-first on recorded days; same day replayed twice gives identical events |
| 2 | Webull live feed, risk gate, paper broker, modeled fills | Guard refuses production host; limits enforced; stale rules fire |
| 3 | API server and plain table view | Real state visible before any 3D |
| 4 | 3D city | Matches the table at all times |
| 5 | Later: flatten button, office scene, Claw3D adapter | |

## 11. Known risks and open items

- Strategy edge is unproven. Earlier research and a 2.6-year option test found ATM option ORB
  roughly break-even on QQQ (not significant) and negative on SPY and IWM. This project builds the
  visibility system and a paper-trading laboratory; it does not assume profit.
- The three triggers are momentum signals on correlated tickers; separate per-bot P&L exists to
  show which, if any, works.
- Webull option order placement, quote freshness in live hours, and history depth are checked in
  phase 0. If option placement fails in the sandbox, fall back to modeled fills (labelled).
- The first-candle-colour direction rule and exact trigger definitions are fixed in the build plan.
