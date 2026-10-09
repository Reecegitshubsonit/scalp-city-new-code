# Contract request: optional `side` on events

From: city view (web3d). To: engine chat. Additive change only.

Add optional field `side` ("CALL" | "PUT" | null) to `tick` and `state_change` events, and to each
bot row in `/snapshot`. Meaning: direction of the setup while `forming`, and of the position while
`fired`, `managing`, `exiting`. `null` or absent when idle, cooldown, locked, paused or stale.

Why: the view colours beams green (CALL) or red (PUT). Without it the view uses a neutral colour and
the text panels cannot say which direction a bot is charging toward.

Optional, lower priority:
- Emit a `control` event on every pause POST, including when the value is unchanged.
- `GET /history?ticker=QQQ`: today's 1-minute closes, so the ticker chart survives a page reload.

Also used by the view (round 2), all optional and additive:
- `mode` on every event ("live" | "replay"): shown as a header badge. The mock sends "mock".
- `pnl` on `trade_closed` (already in the contract): feeds the trade tape, day summary and tower badges.
- `qty`, `contract`, `fill_price`, `fill_source` on `order_sent` and `fill` (already in the contract): shown in the thoughts feed.
- The exit reason (EXIT_STOP, EXIT_TARGET, ...) should arrive on the `exiting` state change; the view remembers it for the trade record.
