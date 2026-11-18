# Option-greek entry hunt

Run 2026-11-17. Script `backtest/greek_hunt.py`, raw output `results.json`.
Source: `data/webull/<day>/snapshots.jsonl`, 22 usable paper days, 22,504 observations across
QQQ, SPY and IWM. Roughly one option-chain snapshot per minute, 30 contracts per snapshot,
carrying implied vol, delta, gamma, theta, bid/ask and volume.

Five features, fixed before the run: ATM implied vol, 25-delta put-minus-call IV skew, 15-minute
change in ATM IV, cumulative put share of option volume, and volume-weighted relative quoted
spread. Three buckets, two horizons: 30 cells, against 135 in the price-based hunt, deliberately.

All returns are excess over the per-ticker drift.

**Result: zero cells pass. No directional edge found.**

## 1. The test, and why it is the right one

With 22 days, a day-level sign test needs **16 of 22** days to reach p<0.05 one-sided. That is
the primary filter here, because bar-level observations within a day are heavily
autocorrelated: 7,500 one-minute bars drawn from 22 days are nothing like 7,500 independent
samples.

A cell had to clear all three: |t| > 3 at bar level, day-sign ≥ 16 of 22, and |mean| above the
0.094 R round-trip cost.

## 2. Bar-level statistics look convincing and mean nothing

| Feature | h | Bucket | n | Mean excess | **t** | **Days with that sign** |
|---|---:|---:|---:|---:|---:|---:|
| iv_skew | 30 | high | 7514 | +0.389 | **+8.76** | **11 / 21** |
| iv_atm | 30 | mid | 7499 | +0.310 | **+6.91** | **12 / 21** |
| iv_atm | 30 | low | 7501 | −0.331 | −6.49 | 10 / 18 |
| iv_skew | 30 | low | 7330 | −0.295 | −6.60 | 12 / 18 |
| pc_volume | 30 | high | 7502 | −0.276 | −6.35 | **7 / 20** |
| pc_volume | 30 | low | 7501 | +0.285 | +5.71 | 8 / 18 |
| rel_spread | 30 | low | 7501 | +0.006 | +0.13 | 13 / 21 |

The strongest cell in the run, 25-delta skew at 30 minutes, carries **t = +8.76 on 7,514
observations and holds its sign on 11 days out of 21.** That is a coin flip.

`pc_volume` is worse: the high-put-volume bucket shows t = −6.35 pooled, and the sign holds on
only **7 of 20 days** — the daily sign disagrees with the pooled sign more often than it
agrees. The pooled number is produced by a few extreme days, not by the feature.

The best day-level consistency anywhere in the table is 14 of 21, on a cell whose effect size
is +0.006 R and t is +0.13 — i.e. noise that happens to lean one way.

## 3. Same failure mode as the price hunt, different data

The price-based hunt (`reports/entry-hunt-2026-11-17`) found candidates that passed a
split-sample test and then held their sign in 6 of 13 months. This one finds candidates with
larger bar-level t-statistics that hold their sign in 11 of 21 days.

Both are the same thing. High IV skew, high put volume, price below the opening range and
falling 15-minute momentum are all **measurements of the same daily regime**. On a down day
they all read one way and forward returns are negative; on an up day they all flip. Pooling
across days makes the regime look like a signal, and the t-statistic measures how many bars
were in down days rather than how predictive the feature is.

Nothing in either hunt identifies the regime in advance, which is the only thing that would
make it tradeable.

## 4. Where this leaves Scalp City

The cumulative picture from 2026-11-17:

| Test | Result |
|---|---|
| Exit shapes, 38 configs, 12 months | No config profitable after measured cost |
| Entry triggers, forward returns | Negative at every horizon; MFE/MAE symmetric |
| Entry filters | All five strongest results negative |
| Market-state hunt, 135 cells | 11 survivors, all one regime effect, sign holds 6/13 months |
| Option-greek hunt, 30 cells | 0 cells pass; best holds 11/21 days |

Four independent angles, one answer: the engine's premise — a 1-minute directional edge on
SPY, QQQ and IWM — is not supported by any data we hold. The exits, the trail parameters, the
per-ticker costs and the instrument mix are all real findings, but they govern how fast money
is lost, not whether.

Honest options from here, in rough order of how much of the existing work they keep:

1. **Change the horizon.** Everything tested is 1 to 30 minutes. Daily or multi-day holds are a
   different competitive field, and the premium model and cost work carry over unchanged.
2. **Change the edge source.** Price and option-chain state are both exhausted here. Scheduled
   events, overnight gaps and cross-asset relationships are untested and need different data.
3. **Stop adding features to this hunt.** Two hunts, 165 cells, both defeated by the same
   regime artifact. A third pass over the same 22 to 250 days will produce more cells that pass
   a pooled test and fail a day test.
4. **Accept the null and keep the infrastructure.** The backtest harness, the cost model, the
   Webull capture and the reporting are sound and reusable against any future hypothesis.

No engine change, no config change, no commit has been made.
