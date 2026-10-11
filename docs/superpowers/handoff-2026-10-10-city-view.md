# Handoff: city view (web3d), 2026-10-10

See the prompt in the chat that created this file; summary of state:

- Done and committed: city view, tower billboards, click-in with full-day chart, backtest room (robot, desk buttons, hex floor, NEVER SLEEPS, 8 screens), replay of logged days, trades panel + EARNED cards + CSV, leaderboard fix, engine endpoints /history /days /day /trades.
- In progress (committed but NOT wired): per-ticker tower rooms. Added `src/model/tower.ts` (+ tests) and in `src/scene/roomPaint.ts`: `paintScanner(..., highlight)`, `paintTickerBoard`, `paintPlaque(..., label)`.
- Not started: wire Room3D/App/ScreenViewer to a ticker scope; "computer-looking" monitors; pronounced FIRE signal.
