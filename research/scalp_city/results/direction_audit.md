# Direction-selection code audit

## Finding

Friday's observed direction behavior is consistent with the earlier cross-only implementation. The current implementation adds EMA9/EMA21 direction selection and passed the offline checks below. No current wiring defect was reproduced for the supplied signal snapshots.

This is a historical strategy/version mismatch relative to today's stated intent. It is not evidence that EMA9/EMA21 direction failed to work when enabled in the current code. The exact Friday process revision/configuration was not recorded, so attribution to a particular deployed revision remains unverified.

## Code evidence

- Before commit `fd474e050a7067cf83e392a1b70711012f5bdd11`, `Bot._evaluate_flat` calls `_fire(bar, ind, view.signal)`. A down-cross therefore directly selects PUT, even with EMA9 above EMA21.
- That commit, recorded October 10, 2026 at 19:36 Mountain, adds `Settings.trend_side=True`, `_side`, and `_fire(bar, ind, self._side(view.signal, ind))`.
- A commit timestamp proves when the change was recorded in Git, not when an uncommitted edit was first written or loaded into a running process. The earlier exporter claim of a Friday 15:16 edit is not established by this audit.
- Current `_side` selects CALL when EMA9 > EMA21 and PUT when EMA9 < EMA21. All nine bots receive the same Settings object through `build_bots`.
- `scripts/run_live.py` constructs Settings with daily-loss/goal overrides only; it does not disable trend_side. This runner does not hot-reload imported Python modules. Editing files cannot by itself change the running engine's imported implementation or its frozen settings instance.
- Engine execution carries `intent.right` into OCC option construction. Tests below confirm the order-side field and option C/P marker remain consistent.

## Concrete Friday example

Trade #1, IWM-VWAP at 09:43: EMA9 = 278.2418 and EMA21 = 278.0604, yet Friday's trade is PUT. The raw VWAP down-cross explains that PUT. Current trend-side code selects CALL at that same snapshot. A full current-rule replay would also change subsequent positions, cooldowns and risk locks; it cannot be valued by flipping the original P&L sign.

## Verification completed

Run `python3 research/scalp_city/audit_direction.py`.

- 52 Friday snapshots: current side selector agrees with EMA direction on all 52; 27 differ from Friday's traded side. With trend_side=False, supplied cross-side inputs are preserved.
- 42 VWAP/EMA50 snapshots: seeded each real trigger with the preceding logged bot snapshot and passed the signal bar through `Bot.on_bar`. All produced the EMA-directed entry under the current default. This isolates direction routing; it is not a complete session replay.
- 36 adversarial order-route cases: all nine bots, both EMA directions, and trend-side enabled/disabled, with the cross deliberately opposed to EMA direction. Entry side, stop/target orientation, and final OCC C/P marker all match the selected mode. This uses supplied trigger views and stub quotes/capture broker; no orders leave the process.
- 36 existing tests passed: `python3 -m pytest tests/test_bot.py tests/test_triggers.py tests/test_config.py tests/test_indicators_contracts.py tests/test_engine_replay.py tests/test_risk_broker.py -q`.

Machine-readable outcomes are in `direction_audit.json`.

## Current edge case and auditability gap

Even with trend_side=True, `_side` falls back to the cross when either EMA is missing or both are exactly equal. A strict trend-only rule would instead skip an entry without a defined trend. None of the 52 Friday snapshots has a missing or equal EMA, so this fallback cannot explain their 27 direction conflicts. Strategy semantics for neutral/invalid inputs should be made explicit in the replay rather than silently changed during this inspection.

The Friday event log lacks an authoritative startup settings/code fingerprint and per-signal raw-cross/selected-side reason. Add this evidence to the replay instrumentation so later comparisons distinguish strategy versions and direction modes reliably. Signal snapshots are rounded; they are sufficient for the observed nonzero gaps here, not proof of exact internal historical float values.

## Consequence for the authorized replay

Preserve separate baselines: Friday raw-cross behavior and the current EMA-direction implementation. Current code also already contains persistent exit_reason handling, which was absent in the earlier version; test the existing fix instead of assuming Friday's exit-retry behavior is still present. Treat the no-opposing-ticker constraint separately: EMA direction at a new entry does not ensure another bot has closed an older opposite position.

This turn inspected and tested code and wrote research artifacts only. It did not change production strategy code or start broker-connected trading.
