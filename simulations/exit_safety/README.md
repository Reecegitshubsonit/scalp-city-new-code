# Exit safety — offline simulation only

User preference: simulate and review fixes before implementation. Do not commit, deploy, restart the bot, or change production behavior as part of this experiment.

This folder contains a candidate exit-controller model, adversarial regression scenarios, and a separate historical exit-lag experiment. No broker calls, credentials, network access, or trading orders are used. Existing production files are imported read-only in baseline regression cases. Hashes in production-before.sha256 verify production files are unchanged.

## Reproduce from repository root

```bash
PYTHONPATH=. .venv/bin/pytest simulations/exit_safety/test_simulation.py -q
.venv/bin/python simulations/exit_safety/historical.py
sha256sum -c simulations/exit_safety/production-before.sha256
```

## Findings

24 offline checks pass. Two reproduce current defects: a failed target exit becomes HOLDING after reversal, and a canceled order with a partial fill returns no fill accounting. Candidate scenarios cover retained exit intent, cancel confirmation before replacement, late fills, remaining quantity after partial fills, duplicate cumulative updates, uncertain submission without fabricated modeled fills, disk restart, position/order mismatch, quote freshness, put thresholds, and independent virtual scheduling.

The actual QQQ-VWAP 11:58–11:59 log sequence preserves TARGET in the candidate even after reversal. This confirms the decision behavior only: the log has no replacement-time option quote, so no improved P&L is asserted.

A synthetic second bot detects a breach at virtual second 2 while the first order remains unresolved through second 15. This demonstrates a nonblocking scheduling contract, not measured threaded production performance. Other tests explicitly show that polling can miss an unobserved touch and that a process outage cannot be repaired by a monitor that is itself offline. No exact stop fill is assumed.

Historical forward split: variants selected on first 60 sessions, evaluated on final 30 sessions. Existing minute-close signal/exit research code is reused with a latched decision and 0/1/2 additional bars before a hypothetical underlying-close exit. Baseline test means are -0.100/-0.105/-0.150 ATR per trade. Selected filters yield +0.025/+0.048/+0.011 gross, and -0.175/-0.152/-0.189 after an assumed 0.2 ATR cost. Day-cluster bootstrap intervals include zero for every gross result. The one-minute improvement in the filtered sample is not evidence that slower execution is better. Costs remain assumptions; returns are underlying ATR, not option dollars.

This reuses the previously examined 90-day sample, so the last 30 days are mechanically held out during selection but are not a fresh, never-seen validation dataset. No claim of newly independent evidence.

## Readiness verdict

Suitable for review and further offline integration, NOT deployment. This is an isolated state-machine prototype; it does not yet provide a production adapter, broker-level order ownership across bots holding the same contract, atomic durable journaling, threaded performance validation, or a shared-production-engine options backtest. The historical experiment does not simulate order reconciliation, option spreads, fees, partial fills, or outages.

A credible option-P&L comparison needs timestamped underlying observations and option bid/ask throughout each position, broker order IDs/status history, actual fill timestamps, effective settings/version, and quote age. Current minute logs cannot supply those counterfactuals. The next simulation stage should connect this controller to a fake broker through a copied production engine, with durable order-ID journaling and account reconciliation, then replay newly collected quote data before any production proposal.

## Integration follow-up

The original prototype limitations above describe the earlier stage. See [DEPLOYMENT.md](DEPLOYMENT.md) for the integrated production-engine candidate, real broker reconciliation, captured-quote accounting replay, shadow runner, and current activation blockers.
