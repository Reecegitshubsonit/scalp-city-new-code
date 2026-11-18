# Scalp City research workspace

Stage: offline, exploratory diagnosis of Friday, October 9, 2026. Purpose: improve the nine existing bots and identify where strategy behavior works against them.

This folder is independent of the production trading engine. It uses Python's standard library, has no network calls, imports no trading modules and needs no credentials.

## Run

From the repository root:

```bash
python3 research/scalp_city/analyze.py
python3 research/scalp_city/analyze_expanded.py
```

Read `results/expanded_report.md` for the current investigation. `results/report.md` preserves the initial table-only diagnosis. Inspect individual trades in `results/trades.csv`, all trial outcomes in `results/experiments.csv`, exact memberships in `results/metrics.json`, and source/code hashes in `results/manifest.json`. The script overwrites only its generated results. Raw input and experiment definitions are kept separately.

## Source contract

- Authoritative numerical input: the user's pasted 52-row table, copied unchanged into `data/friday_2026-10-09.tsv`.
- Session date confirmed by user: 2026-10-09. Signal times interpreted as Eastern from the original report context.
- Three restart positions are outside scope by explicit user instruction. Do not add them or use this sample as total account performance.
- All 52 supplied rows are included, including starred rows. Starred-fill exclusion is a separately labeled sensitivity analysis.
- Opposing positions are unintended. Same-direction overlap has not been prohibited.
- User has already tested settings without finding profitability. This sample and previously explored historical periods are development evidence, not untouched validation.
- Definitions only: `reports/dissect-2026-10-09/signal_table.py`, `setup_puts.py`, and `dissect.py` explain column construction. They are not executed or used to supply additional numerical observations.
- Intended behavior only: `/home/ronaldsecret/Master prompt/trading-strategy-master-prompt.pdf` and present code. Neither establishes the actual Friday runtime configuration. The master prompt remains authoritative for goals and risk constraints; this workspace does not rewrite it.

## Interpretation

Screening is **subset analysis**, not a backtest. Keeping some historical trades does not simulate altered future triggers, exits, lockouts, cooldowns, risk reservations or fills. All six explored screens are registered in `experiments.json`, including losing outcomes. Registration happened after inspecting the data; it is not a preregistration claim.

Do not infer option returns from underlying ATR moves. Do not count trades across correlated bots as independent observations. Do not treat entry-ordered cumulative P&L as account equity or drawdown. The table does not give exits, position size, option premiums, fees, ordered price paths or concurrent holdings.

A filter must improve average outcome and risk at comparable exposure on fresh chronological evidence, not merely reduce total losses by taking fewer trades. A positive retained sum here is insufficient for promotion. Account-risk simulation also needs open-position and pending-order state.

## Next experiments

1. Confirm actual Friday side-selection configuration against the 27 apparent EMA-direction conflicts.
2. Validate no opposing ticker exposure using disconnected ordered-event replay; model existing positions and pending entries and preserve risk-reducing exits.
3. Investigate the interaction of PUT direction and squeezed EMAs across new sessions. Avoid selecting a PUT-only squeeze rule solely because it fits Friday.
4. Separate stops with immediate adverse movement from those with favorable movement before the exit; use ordered paths before testing modified stops or targets.
5. Test stable candidate rules on new chronological sessions with actual option quote costs where available. Record every meaningful attempt and retain failed results.

No broker-connected session, automated recurring job, paid retrieval or production setting change is part of this research run.

## Expanded evidence update

The supplied expanded CSVs are frozen in `data/expanded`. `analyze_expanded.py` validates the 52 rows and 104 fill records against Friday’s raw log, verifies the 622 path observations, computes opposing pairs, records a no-opposing historical-entry sensitivity, and benchmarks the original screens using order quotes. See `results/expanded_manifest.json` for source hashes, `expanded_metrics.json` for exact memberships, `opposing_pairs.csv`, and `exit_diagnostics.csv`.

Earlier missing-data statements describe the original table-only stage. The expanded evidence now supports ordered underlying paths and bar-minute holding intervals, but still does not provide actual execution wall-clock times, fees, guaranteed quote-price fills, or complete historical options quotes for alternative exits. Both scripts run offline. Original expanded exports remain unchanged; export interpretation corrections are documented in the new report.

The no-opposing test is exploratory, registered during analysis. Its rule is to keep original fill sequence order and exit records and omit a later opposite entry while an earlier retained position is open. It is a behavior diagnostic with fixed historical exits, not a full strategy replay. It is not considered a profitable improvement unless later full replay demonstrates improved results at comparable exposure; compliance with intended behavior is assessed separately from P&L.

## Direction implementation audit

Run `python3 research/scalp_city/audit_direction.py` for offline snapshot/trigger/order-route checks. Read `results/direction_audit.md` for Git evidence, current behavior, neutral-EMA fallback, and the distinction between Friday and current replay baselines. This audit imports production classes with fake quotes and a capture broker; it does not import the broker client or connect externally.

## Disconnected replay

The completed offline retry/coordination/entry study is in `replay/results/report.md`. See `replay/README.md` for reproduction and the distinction between actual paper outcomes and hypothetical underlying signal replay. All 64 trial variants and control tests are retained.
