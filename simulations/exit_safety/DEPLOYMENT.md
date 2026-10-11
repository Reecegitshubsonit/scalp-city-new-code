# Candidate integration and deployment status

Simulation first. No commits, live-file modifications, account mutations, or service restarts were performed. The existing working-tree edits predate this work.

## What is now verified

- A frozen copy of the production scalpcity package is in candidate/scalpcity. SafeEngine subclasses that production Engine. Entry signals, indicators, risk checks, bot accounting, and event projection execute through the actual engine code.
- 33 integration/adapter/shadow tests pass, including an actual bar-driven signal → asynchronous entry fill → risk-monitor exit → realized P&L cycle. Tests also cover same-contract ownership across bots, partial entry cancellation, partial exits and changing average fill prices, late fills, unknown submission, cancel acknowledgement, restart reconciliation, atomic persistence failure, duplicate journal writers, configuration mismatch, stale/invalid quotes, duplicate fills, and pause persistence.
- All 78 original regression tests pass against the candidate package: 75 ordinary tests and 3 local-server tests. The server tests required an unrestricted local test-client environment; the initial restricted run stalled rather than reporting a code failure.
- 90 seconds of read-only Webull market snapshots were captured (90 request records, one request error). Eight replay scenarios use actual observed option bid/ask, source timestamps, displayed size, 0/0.5/1/2-second latency assumptions, and two explicit fee assumptions. All eight engine P&L results match independent cash flows. Stale quotes are rejected; prices are never filled from future observations or fabricated from trade bars. This uses a seeded QQQ 751 put test position and artificial test thresholds; it is accounting/execution-path validation, NOT proof of profitable strategy behavior.
- Broker evidence: 109 historical orders returned; 108 were option orders. 89 of 97 logged fills matched unique broker records using contract, side, quantity, price, and time. Four remain unmatched and four ambiguous. Forty-one fully matched closed trades reconcile to -$1,420 gross, $39.93 broker fees, -$1,459.93 net. This subset is NOT total session P&L. Sandbox fills confirm accounting, not real-market fill quality.

## Candidate behavior

SafeEngine journals stable client order IDs before submission, records decision/observation/quote/broker-fill timestamps, and runs broker I/O on worker threads outside the engine lock. Exit decisions remain latched through reversals. Cancellation must reach a broker terminal state before replacement. Cumulative quantity/notional/fee accounting applies incremental executions once and retains the remaining position. Unknown outcomes halt submissions pending account reconciliation; there is no modeled-fill fallback. State snapshots use write/fsync/rename/directory-fsync, with an exclusive journal lock. Pauses and effective settings are persisted. Legacy log-only recovery is explicitly rejected.

PaperAdapter generates the existing Webull single-leg LIMIT payload with the pre-journaled client ID. It accepts only the sandbox guard configuration, parses the captured Webull fee/quantity/timestamp schema, and retrieves order status after cancellation. Submission/cancellation were tested with injected fakes only: no sandbox orders were sent. It requires a dedicated options paper account; unknown assets/orders are not silently ignored.

## Activation is BLOCKED

The candidate is reviewable but cannot honestly be certified ready for order activation:

1. At the read-only 14:13 ET snapshot, the broker held **30 QQQ261012P00749000** contracts while the log accounted for **20**. Ten contracts have no established ownership in the log. The account also contains a QQQ equity holding outside the options engine. Do not auto-liquidate, adopt, or erase these positions to make a check pass.
2. Eight old logged fills cannot be uniquely reconciled without stable order IDs. The new candidate supplies those IDs going forward but cannot invent missing historical lineage.
3. Ninety seconds on one seeded contract validates accounting, not full-session execution distributions or positive expectancy. Collect representative sessions of underlying observations and option bid/ask with timestamps, sizes, and feed provenance. Re-run the same engine with recorded strategy signals and fees; fail coverage checks when required quotes are absent. Alpaca's documented option interface supplies latest quotes plus historical bars/trades; indicative quotes are not actual OPRA quotes.
4. The sandbox adapter's real submit/cancel round trip has not been exercised because the user requested simulation before implementation. An isolated sandbox smoke test requires a later explicit transition from this no-order scope, using an empty/dedicated account and reviewed quantities.
5. Before startup, obtain a fresh complete broker snapshot, resolve every tracked order, and match aggregate inventory. A historical reconciliation artifact cannot authorize future orders.

## Reproduce

From /home/ronaldsecret/scalp-city:

```bash
.venv/bin/python -m pytest -q simulations/exit_safety/integration_tests --override-ini pythonpath=simulations/exit_safety/candidate
.venv/bin/python -m pytest -q tests --override-ini pythonpath=simulations/exit_safety/candidate
.venv/bin/python simulations/exit_safety/quote_replay.py
.venv/bin/python simulations/exit_safety/candidate/preflight.py
sha256sum -c simulations/exit_safety/evidence/production-before.sha256
```

Preflight intentionally returns exit code 2 while activation checks remain false. It is an evidence report, not an activation launcher. Do not edit a boolean to bypass an unresolved check.

## Proposed activation / rollback sequence (not executed)

Resolve broker/log ownership first; preserve unrelated holdings. Use a dedicated flat paper account, snapshot configuration and candidate hashes, then perform reviewed adapter submission/cancel smoke tests. Use the candidate runner and its cached quote source, warm indicators without entries, load only candidate durable state, reconcile, and begin a bounded paper run. Existing scripts/run_live.py still selects the old Engine and MUST NOT be used to activate this candidate. candidate/run_candidate.py now provides a separate bounded shadow/paper runner with independent quote and bar workers and a cached quote source. Its default is shadow mode; --mode paper refuses activation while release checks fail. Prolonged forward validation and the account/adapter checks above remain required before order activation.

On failure, halt new entries and retain the authoritative journal and broker IDs. Reconcile outstanding orders/positions before any cancellation, retry, or engine switch. Do not revert a running account to the old log-only recovery engine while candidate orders or positions remain unresolved.

Sources: https://docs.alpaca.markets/us/docs/historical-option-data and https://alpaca.markets/sdks/python/api_reference/data/option/historical.html . Broker/quote evidence was retrieved read-only from the user's configured Webull sandbox; private raw snapshots remain under ignored data/exit-safety/.

## Shadow-only runner

`candidate/run_candidate.py --mode shadow --seconds 70 --output <fresh directory>` consumes read-only sandbox market data and fills only through a local ShadowAdapter. That adapter has no remote order client. Shadow bid/ask fills remain simulation assumptions. Its output captures market observations, event logs, durable state and a summary. See evidence/release-gate.json for the evaluated runner smoke test. No paper activation was attempted beyond verifying that its gate refuses to proceed.

## Additional reconciliation detail

For QQQ261012P00749000, broker history contains a filled 10-contract BUY placed at 10:12:23 ET with no corresponding local fill event. A separate BUY placed at 10:12:04 is canceled. Without logged order IDs, this must not be described as a proven late fill of the canceled order. It contributes to the unexplained 10-contract inventory difference. The four unmatched logged fills also have price conflicts: the two 10:02 entry events record 3.16/3.15 while nearby broker buys record 3.01/2.92, and the two 10:07 exits record 2.84/2.88 while nearby broker sells record 2.99/2.98. These are unresolved conflicts, not silently corrected trades.

The 70-second integrated shadow smoke completed with 3 completed bars, 37 underlying snapshot batches, 36 option snapshot batches, zero feed errors and zero remote order calls. The shorter preceding 20-second smoke also completed without errors. This confirms the runner's market-data wiring; it does not claim strategy-trade coverage during those brief windows.
