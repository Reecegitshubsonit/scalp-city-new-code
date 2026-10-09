# City View Round 2 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Close the gaps between `web3d/` and the reference recording (structure and behaviour only; every asset procedural, no names or assets from the video).

**Architecture:** Add pure, tested text/summary functions to `src/model/`; extend the reducer (previous state on feed events, closed-trade list, chart overlays); add HTML panels (scanner room, ticker charts, heatmap, tape, day summary); upgrade the scene (signs, badges, taller beams, lattice towers, orbit rings, link lines, bigger fire flash, camera fly-in, clickable dome).

**Spec:** `docs/superpowers/specs/2026-10-08-city-view-design.md` plus the gap list from the 2026-10-09 re-watch.

## Global Constraints
- Same as `2026-10-08-city-view.md` (paper only, procedural only, reduced motion, text never colour alone, title default "Scalp City" configurable).
- Day goal for the summary: $5,000 fixed (user choice), constant `DAY_GOAL` in `src/model/summary.ts`.
- Commits end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Tasks
1. **Text model (tests first):** `thoughts.ts` (`thoughtText(ev)`), `headline.ts` (`headline(row)`), `badge.ts` (`badgeFor(row, lastTrade)`), `summary.ts` (`daySummary`, `DAY_GOAL`).
2. **Reducer extensions (tests first):** `prev_state` on feed events; `exit_code` on rows; `trades: TradeRec[]` (cap 100); tick points carry `vwap`/`ema50` (not taken from a forming bot); marks carry `side`, exit dedupe.
3. **Panels:** `Room` (scanner headline, charge bar, sentence thoughts for that bot, inputs, chart; replaces Drawer), `Charts` (3 tickers, price + VWAP + EMA50, % change, markers), `Heatmap`, `Tape`, `Summary`, sentence `Feed`.
4. **Scene:** trigger signs, event badges, beam max 16 with glow shell, lattice pylons and antenna, orbit rings, link lines, big fire flash, platform spokes, dome click, camera fly-in to selected tower.
5. **Verify:** tests, build, mock run in browser pane, 60 fps, reduced motion, README and screenshots refreshed.
