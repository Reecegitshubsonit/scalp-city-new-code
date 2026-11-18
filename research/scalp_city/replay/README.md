# Disconnected replay research

Start with `results/report.md`.

The actual 52-trade ledger remains separate from an observed-indicator, stateful underlying replay. This workspace tests exit retry decisions, ticker-direction ownership, and entry variants in that order. No broker access or production mutation occurs.

## Reproduce

From the repository root:

```bash
python3 research/scalp_city/replay/run.py
python3 research/scalp_city/replay/report.py
python3 -m pytest research/scalp_city/replay/test_replay.py -q
python3 -m pytest simulations/exit_safety/integration_tests -q
```

Python standard library plus pytest for tests. No `.env`, credentials, broker startup, network retrieval or paid data.

- `plan.json`: experiment plan written before the first run, after Friday had already been examined.
- `stress_followup.json`: explicitly later robustness additions, not preregistered.
- `run.py`: production Bot decision/state transitions, earlier-exit subclass, snapshot replay, all variants.
- `coordination.py`: isolated direction-ownership reservation prototype.
- `test_replay.py`: adversarial and causal checks.
- `results/replay.json`: all states needed to inspect trades, exits, vetoes and scenarios.
- `results/summary.csv`, `trades.csv`, `by_bot.csv`: all trial results; no losing trials hidden.
- `results/manifest.json`: source hashes and unchanged production hashes.

Signal replay does not model option dollar P&L or monetary account safeguards. It cannot validate $800 trade/$1,500 daily account limits, four-loss timing net of costs, or deployability. Production limits are unchanged. It uses hypothetical underlying-close fills and inherits recorded indicators; reconstructed opening ranges and missing observations are explicit limitations. The exact factual account replay is unavailable from these records, and the 64-trade modeled baseline must not be confused with 52 actual trades. The three user-excluded restart entries are blocked across all variants.
