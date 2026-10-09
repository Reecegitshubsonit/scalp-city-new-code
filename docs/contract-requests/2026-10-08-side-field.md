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
