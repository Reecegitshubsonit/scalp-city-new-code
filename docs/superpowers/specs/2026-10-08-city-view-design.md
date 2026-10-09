# City view (web3d): design spec

Front end for the Scalp City paper-trading engine. Read-only view plus one control (pause).
Source of truth for data: `2026-10-08-scalp-city-design.md` (section 9) and the engine plan
(Task 13 API server, Task 14 table view). The engine is not built yet, so the view is developed
against a mock server that speaks the same API.

## 1. Scope and hard rules

- In scope: `web3d/` front end, `web3d/scripts/mock_stream.mjs`, unit tests, README, one contract note.
- Out of scope: engine, broker code, API server. No code places orders. No keys, no `.env`.
- Procedural geometry only. No downloaded models or textures. No assets taken from the reference
  recording. Original look.
- Title is configurable (`VITE_TITLE`, or `?title=` query). Default "Scalp City" (user instruction,
  2026-10-08).

## 2. Layout (laptop width ~1366 px)

- Header: title, market clock (open 9:30 ET, close 16:00 ET, countdown), data-freshness, "table only"
  toggle, connection status.
- Left 80 %: 3D canvas on top; 9 bot cards below (3 columns, grouped by ticker).
- Right 20 %: leaderboard (by `pnl_day`), thoughts feed (events with kind other than `tick`, newest
  first).
- Detail drawer slides over the right column when a bot is selected (click tower or card; Esc
  closes). Shows inputs: price, vwap, ema9, ema21, ema50, atr, distance_atr, plus reason, charge,
  and the ticker chart.
- Below 1100 px width the right column moves under the cards.
- "Table only" hides the canvas; cards grow to fill the space. Every state has a text label and an
  icon, never colour alone. All controls are keyboard operable with visible focus.

## 3. City

- Palette: ground `#0b0830` indigo, faint grid, fog, bloom (postprocessing). CALL green, PUT red,
  no side = neutral violet-white.
- Ring platform; 3 districts at 120 degrees (QQQ, SPY, IWM), 3 towers each (VWAP, EMA50, RANGE).
  Tower = base block + two setbacks + spire; windows from a procedural shader, deterministic per bot.
- Centre dome: day P&L (sum of `pnl_day`), tinted green/red/neutral, label above.
- Orbit camera with slow auto-rotate while idle (off under reduced motion). Click a tower to select.
- Floating labels: P&L over managing towers; short tag for locked / stale / paused.

State to visual:

| state | look |
|-------|------|
| idle | dim tower, ~15 % window light |
| forming | beam height = charge_pct (0-100), colour by side |
| fired | one ring flash (~1 s) |
| managing | steady glow in side colour, floating P&L label |
| exiting | pulsing glow |
| cooldown | blue |
| locked | amber |
| paused | hatched, grey |
| stale | flickering red |

Reduced motion: no flash, pulse, flicker or auto-orbit. Same states as static colour plus steady
beam; the fired ring is a static ring held for 2 s.

### Side (green/red) resolution

Beam and glow colour come from `resolveSide`, first match wins:
1. explicit `side` on the event or snapshot row;
2. CALL/PUT parsed from reason_text of a `SIGNAL` event (engine writes "CALL signal at 123.45"),
   remembered until the position closes or the bot goes idle/cooldown/locked/paused/stale;
3. forming only, VWAP and EMA50 bots: price below level = CALL (next cross is up), above = PUT;
4. otherwise neutral.
Rule 3 is an inference (engine `distance_atr` is unsigned), and RANGE has no level in `inputs`, so
RANGE forming is neutral until the engine sends `side`. The drawer says "side: inferred" when 2 or 3
was used.

## 4. Panels (HTML, carry every exact number)

1. Bot cards: state chip, reason_code + plain-words reason_text, charge %, price, day P&L, trades,
   last update, Pause/Resume.
2. Thoughts feed.
3. Leaderboard.
4. Market clock + freshness (age of newest event or tick; amber over 90 s, red over 180 s during
   market hours; thresholds are constants).
5. Detail drawer, including a per-ticker chart: price line from `tick` events of that ticker (last
   ~390 points), markers from `order_sent`/`fill` (entry) and `trade_closed` (exit). SVG, no chart
   library. Built from events seen since page load plus snapshot price (history is not in the API;
   see contract notes).

## 5. Data flow

`net/` holds the fetch and WebSocket client; `model/reducer` is a pure function
`(state, message) -> state`.

- Load: `GET /snapshot` seeds rows and `last_seq`. WS `snapshot` message replaces all rows and
  resets `last_seq` (reconnect re-applies it).
- WS `event`: ignored when `seq <= last_seq` (duplicate or out of order). Otherwise it updates the
  row fields it carries: state, reason_code, reason_text, charge_pct, inputs, time, side on `tick`
  and `state_change`; `pnl_day`, `trades` whenever present; `paused` on `control`. Non-tick events
  also go to the feed (capped at 200).
- Unknown bot id in an event: ignored. Unknown reason code: shown as the code text. `charge_pct`
  null: no beam, "-" in text.
- Reconnect: exponential backoff 1 s to 15 s with jitter; on open the snapshot message is applied.
- Pause: `POST /control/pause {bot, paused}`. The button shows pending; the row flips when the
  resulting `control` event arrives over WS (not from the POST response). 404 shows an error toast.
  Pending clears on event, on error, or after 5 s.

## 6. Code layout

```
web3d/
  src/model/   types.ts reasons.ts visual.ts reducer.ts format.ts      (pure, tested)
  src/net/     api.ts socket.ts
  src/scene/   City.tsx Tower.tsx Beam.tsx Dome.tsx Ring.tsx
  src/panels/  Cards.tsx Feed.tsx Leaderboard.tsx Clock.tsx Drawer.tsx Chart.tsx
  src/App.tsx  main.tsx styles.css
web3d/scripts/mock_stream.mjs
docs/contract-requests/2026-10-08-side-field.md
```

Tests (vitest): `visual` (state to colour, beam height, label text), `reasons` (known and unknown
codes), `reducer` (snapshot + events, duplicate/out-of-order seq, null charge, unknown bot,
reconnect snapshot, control event), `format`.

## 7. Mock server

Node script, same three endpoints, `--speed N`, `--port`, default 8000. Scripted synthetic day with
all states: forming with rising charge, fire, hold, each exit kind, cooldown, a daily lock, a stale
bot, a paused bot (via POST), and a scheduled disconnect (closes sockets, stays down a few seconds,
returns). Seq is monotonic across the run.

## 8. Contract notes and guesses (also reported to the user)

1. `side` ("CALL"|"PUT"|null) is not in the engine contract. Requested as an additive optional
   field on `tick` and `state_change`. Written to `docs/contract-requests/`. Absent = neutral colour.
2. Plan Task 13 `POST /control/pause` returns `{ok, bot, paused}`, not an event. The view takes the
   row update from the `control` event on the WS. If the engine does not emit it when the value is
   unchanged, the button clears via the 5 s timeout.
3. The engine's table view updates `pnl_day`/`trades` on `trade_closed`; this view accepts them on
   any event that carries them.
4. No price history endpoint. The ticker chart only shows ticks since page load. Request (optional):
   `GET /history?ticker=QQQ`.
5. Snapshot rows before any event have `time: null`, `inputs: {}`; the view must render them.
6. The engine serves `web/` statically. The built `web3d/dist` is not wired into it; that is the
   engine chat's call.
7. Event `time` is ISO in ET; the view displays it as given and does not convert zones.
8. Spec section 9 mentions a heatmap; not in the brief, not built.
