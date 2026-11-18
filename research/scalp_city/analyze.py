"""Offline, standard-library research on the user's 52-row session table.
Run: python3 research/scalp_city/analyze.py
No strategy imports, broker connectivity, or trading-system mutations.
"""
from pathlib import Path
import csv
import hashlib
import json
import re
import platform
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'data/friday_2026-10-09.tsv'
OUT = ROOT / 'results'


def read_rows():
    rows = []
    with SOURCE.open(newline='') as f:
        for raw in csv.DictReader(f, delimiter='\t'):
            number = raw['#']
            atr = re.fullmatch(r'([\d.]+) \(([\d.]+)\)', raw['ATR (bp)'])
            time, price = raw['signal'].split(' @ ')
            best, worst = map(float, raw['best/worst'].split('/'))
            post_best, post_worst = map(float, raw['30m after exit'].split('/'))
            ticker, trigger = raw['bot'].split('-')
            ema_direction = 'CALL' if raw['EMA9/21'].startswith('9>21') else 'PUT'
            share = float(raw['above VWAP 30m'].rstrip('%'))
            row = dict(id=int(number.rstrip('*')), flagged='*' in number,
                       bot=raw['bot'], ticker=ticker, trigger=trigger,
                       side=raw['side'], time=time, price=float(price),
                       pnl=int(raw['P&L']), result=raw['result'],
                       atr=float(atr[1]), atr_bp=float(atr[2]),
                       vwap=raw['VWAP'], ema50=raw['EMA50'], slope=raw['EMA50 slope'],
                       range=raw['range'], ema_direction=ema_direction,
                       ema_gap=float(raw['EMA9/21'].split()[1]),
                       squeeze='SQUEEZE' in raw['EMA9/21'],
                       above_vwap_share=share,
                       pre5=None if raw['run before']=='n/a' else float(raw['run before']),
                       best=best, worst=worst, post_best=post_best, post_worst=post_worst)
            row['ema_agrees'] = row['side'] == ema_direction
            row['vwap_conflict'] = (row['side']=='PUT' and share>=80) or (row['side']=='CALL' and share<=20)
            row['period'] = 'Before 11:00' if time<'11:00' else '11:00–11:59' if time<'12:00' else '12:00 onward'
            rows.append(row)
    if [r['id'] for r in rows] != list(range(1,53)):
        raise ValueError('Expected supplied IDs 1..52 exactly once')
    if any(r['side'] not in ('CALL','PUT') or r['result'] not in ('stop','target') for r in rows):
        raise ValueError('Unexpected side or result')
    if any(r['best']<0 or r['worst']>0 or r['post_best']<r['post_worst'] for r in rows):
        raise ValueError('Invalid excursion fields')
    return rows


def stats(rows):
    n = len(rows)
    positive = sum(r['pnl'] for r in rows if r['pnl']>0)
    negative = -sum(r['pnl'] for r in rows if r['pnl']<0)
    wins = sum(r['pnl']>0 for r in rows)
    losses = sum(r['pnl']<0 for r in rows)
    return dict(n=n, pnl=positive-negative, wins=wins, losses=losses,
                win_pct=100*wins/n if n else None,
                targets=sum(r['result']=='target' for r in rows),
                average=(positive-negative)/n if n else None,
                average_win=positive/wins if wins else None,
                average_loss=negative/losses if losses else None,
                profit_factor=positive/negative if negative else None,
                ids=[r['id'] for r in rows])


def grouped(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    return {k:stats(v) for k,v in sorted(groups.items())}


def fmt(v, decimals=1):
    return 'n/a' if v is None else f'{v:,.{decimals}f}'


def table(groups):
    lines = ['| Group | Trades | Positive P&L | Target exits | Reported P&L | Avg/trade | Profit factor |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for k,s in groups.items():
        lines.append(f"| {k} | {s['n']} | {fmt(s['win_pct'])}% | {s['targets']} | ${s['pnl']:+,} | ${fmt(s['average'])} | {fmt(s['profit_factor'],2)} |")
    return '\n'.join(lines)


def main():
    OUT.mkdir(exist_ok=True)
    rows = read_rows()
    baseline = stats(rows)
    groups = {
        'Nine bots': grouped(rows,lambda r:r['bot']),
        'Side': grouped(rows,lambda r:r['side']),
        'Trigger': grouped(rows,lambda r:r['trigger']),
        'Ticker': grouped(rows,lambda r:r['ticker']),
        'Time of signal': grouped(rows,lambda r:r['period']),
        'EMA9/21 alignment': grouped(rows,lambda r:'Agrees' if r['ema_agrees'] else 'Opposes'),
        'Squeeze': grouped(rows,lambda r:'Labeled squeeze' if r['squeeze'] else 'Not labeled squeeze'),
        'Persistent VWAP conflict': grouped(rows,lambda r:'Against persistent side' if r['vwap_conflict'] else 'No persistent conflict'),
        'ATR': grouped(rows,lambda r:'Below 3 bp' if r['atr_bp']<3 else 'At least 3 bp'),
        'Side and squeeze': grouped(rows,lambda r:r['side'] + (' / squeeze' if r['squeeze'] else ' / no squeeze')),
        'Opening range and side': grouped(rows,lambda r:r['side']+' / '+r['range']),
        'Prior five-minute move': grouped(rows,lambda r:'Missing' if r['pre5'] is None else 'Against trade direction' if r['pre5']<0 else '0 to less than 1 ATR' if r['pre5']<1 else 'At least 1 ATR'),
        'EMA50 slope alignment': grouped(rows,lambda r:'Missing' if r['slope']=='n/a' else 'Rounded flat' if float(r['slope'].split()[1])==0 else 'Agrees' if (r['slope'].startswith('up') == (r['side']=='CALL')) else 'Opposes'),
    }
    predicates = {
        'E01':lambda r:r['ema_agrees'],
        'E02':lambda r:not r['squeeze'],
        'E03':lambda r:not r['vwap_conflict'],
        'E04':lambda r:r['ema_agrees'] and not r['squeeze'],
        'E05':lambda r:not r['squeeze'] and not r['vwap_conflict'],
        'E06':lambda r:r['atr_bp']>=3,
    }
    registry = json.loads((ROOT/'experiments.json').read_text())
    trials = []
    for spec in registry['experiments']:
        keep = [r for r in rows if predicates[spec['id']](r)]
        reject = [r for r in rows if not predicates[spec['id']](r)]
        trials.append(dict(**spec, retained=stats(keep), removed=stats(reject),
                           retained_unflagged=stats([r for r in keep if not r['flagged']])))
        assert stats(keep)['pnl']+stats(reject)['pnl']==baseline['pnl']
    clusters=defaultdict(list)
    for r in rows:
        clusters[(r['ticker'],r['time'],r['side'],r['price'])].append(r)
    duplicates=[v for v in clusters.values() if len(v)>1]
    first=[v[0] for v in clusters.values()]
    last=[v[-1] for v in clusters.values()]
    stopped=[r for r in rows if r['result']=='stop']
    diagnostics = {
        'all':baseline,
        'unflagged':stats([r for r in rows if not r['flagged']]),
        'flagged':stats([r for r in rows if r['flagged']]),
        'stops':stats(stopped),
        'stops_best_at_least_1atr':stats([r for r in stopped if r['best']>=1]),
        'stops_best_at_least_2atr':stats([r for r in stopped if r['best']>=2]),
        'stops_best_below_quarter_atr':stats([r for r in stopped if r['best']<.25]),
        'stops_worst_below_minus_1atr':stats([r for r in stopped if r['worst']<-1]),
        'stops_post_best_at_least_2atr':stats([r for r in stopped if r['post_best']>=2]),
        'duplicate_groups':[[r['id'] for r in v] for v in duplicates],
        'signal_clusters':len(clusters),
        'dedup_first_row':stats(first), 'dedup_last_row':stats(last),
        'groups':groups,'experiments':trials,
    }
    for g in groups.values():
        assert sum(s['n'] for s in g.values())==52
        assert sum(s['pnl'] for s in g.values())==baseline['pnl']
    (OUT/'metrics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    with (OUT/'trades.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    experiment_rows=[]
    for t in trials:
        for cohort in ('retained','removed','retained_unflagged'):
            experiment_rows.append(dict(id=t['id'],name=t['name'],cohort=cohort,**t[cohort]))
    with (OUT/'experiments.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(experiment_rows[0])); w.writeheader(); w.writerows(experiment_rows)
    lines = ['# Friday research baseline — October 9, 2026',
        '', '**Scope:** 52 supplied closed trades only. The three restart positions are excluded by user instruction. This is not complete account P&L.',
        '',f"Reported P&L: **${baseline['pnl']:+,}**. {baseline['wins']}/52 positive outcomes (**{baseline['win_pct']:.1f}%**); {baseline['targets']}/52 target exits. Average reported P&L **${baseline['average']:.2f}** per trade; profit factor **{baseline['profit_factor']:.2f}**.",
        '', '## What this session establishes',
        '', f"PUT trades account for ${groups['Side']['PUT']['pnl']:+,}, versus ${groups['Side']['CALL']['pnl']:+,} for CALLs. The strongest observed interaction is squeezed PUT entries: {groups['Side and squeeze']['PUT / squeeze']['n']} trades, ${groups['Side and squeeze']['PUT / squeeze']['pnl']:+,}. This is a concentration of losses, not proof that squeeze or direction alone caused them. Both squeezed CALLs won, illustrating the danger of generalizing one aggregate filter.",
        '', f"QQQ-VWAP and SPY-EMA50 together contribute ${groups['Nine bots']['QQQ-VWAP']['pnl']+groups['Nine bots']['SPY-EMA50']['pnl']:+,} over {groups['Nine bots']['QQQ-VWAP']['n']+groups['Nine bots']['SPY-EMA50']['n']} trades. Those are priorities for review, not sufficient evidence to disable the bots permanently.",
        '', f"Average positive outcome is ${baseline['average_win']:.2f}; average negative outcome magnitude is ${baseline['average_loss']:.2f}. Their observed payoff ratio is {baseline['average_win']/baseline['average_loss']:.2f}:1. Holding these averages fixed would require a {100*baseline['average_loss']/(baseline['average_win']+baseline['average_loss']):.1f}% positive-outcome rate to break even, versus the observed {baseline['win_pct']:.1f}%. This is arithmetic on reported P&L, not a forecast or cost-adjusted required win rate.",
        '', f"The table contains {groups['EMA9/21 alignment']['Opposes']['n']} trades whose side opposes the reported fast-EMA direction. That differs from the intended trend_side=True rule, but filtering to aligned trades still loses ${abs(groups['EMA9/21 alignment']['Agrees']['pnl']):,}. The data does not support the claim that alignment alone fixes the strategy; reversing historical trades is a different, untested experiment.",
        '', 'The only positive full-sample entry screen leaves $40 across 32 trades; excluding flagged fills turns it negative. None of the six screens demonstrates a robust profitable strategy. Most stop exits have little favorable movement or path overshoot; the exact contribution of stop timing versus execution needs ordered data.',
        '', '## Definitions and evidence boundaries',
        '', 'Reported P&L is the supplied dollar column; fee inclusion, size and option entry premium are unknown. Profit factor = sum of positive P&L / absolute sum of negative P&L. Average loss is expressed as a positive magnitude. A winning dollar result and a target exit are different measures. No option-premium return, actual R-multiple, annualized result or account drawdown is inferred.',
        '', 'The existing table generator identifies distances and excursions as underlying-price movement in signal-time ATR units, signed in the trade direction. Best/worst summarize observed closes during the trade, not executable option prices or necessarily intrabar extrema. The post-exit column is measured relative to the original signal price, not the exit price. EMA50 slope is a 20-minute change divided by signal ATR. The above-VWAP lookback uses available observations in an inclusive 31-minute window; early-session percentages can represent much shorter history. Treat rounded zeros and 0.15 gap boundary values cautiously; use supplied squeeze labels.',
        '', 'One session supplies one market-day observation. Trades within a ticker/session are dependent. No confidence interval or significance claim based on 52 independent trades is justified here. Prior settings were already explored in backtests; existing history cannot automatically be called untouched holdout data.',
        '', '## Fill-flag sensitivity', '',table({'All supplied':baseline,'Three flagged rows':diagnostics['flagged'],'Exclude flagged rows':diagnostics['unflagged']}),
        '', 'Flagged rows remain in the primary sample. Their asterisks come from the supplied table; local generator metadata labels them off-market fills. They are not the three excluded restart positions. Exclusion is a sensitivity check, not a corrected execution result.',
        '', '## Performance decomposition']
    for name,g in groups.items():
        lines.extend(['',f'### {name}','',table(g)])
    lines.extend(['','## Exit-path diagnostics','',
        f"Of {len(stopped)} stop-labeled trades, {diagnostics['stops_best_below_quarter_atr']['n']} never reached +0.25 ATR in the summarized path, {diagnostics['stops_best_at_least_1atr']['n']} reached at least +1 ATR, and {diagnostics['stops_best_at_least_2atr']['n']} reached at least +2 ATR (rounded). These are overlapping diagnostic counts, not additive categories.",
        '',f"{diagnostics['stops_worst_below_minus_1atr']['n']} stop trades have a worst observed close below -1 ATR. This identifies path overshoot; it does not quantify option slippage or prove the fill occurred at the worst point. {diagnostics['stops_post_best_at_least_2atr']['n']} stopped trades show a post-exit best of at least +2 ATR relative to entry.",
        '', 'Extrema lack event ordering. A +1 ATR favorable excursion does not prove a tighter target would have filled before the original stop. Neither a trailing-stop backtest nor a side-flipped return can be reconstructed from these summary fields. Do not use best/worst or post-exit movement as entry features.',
        '', '## Duplicate signals and opposing positions',
        '',f"There are {len(clusters)} unique ticker/time/side/price clusters. Same-signal groups: {diagnostics['duplicate_groups']}. Keeping the first listed row per cluster gives ${stats(first)['pnl']:+,}; keeping the last gives ${stats(last)['pnl']:+,}. Both are bookkeeping sensitivities with less exposure, not replay results or evidence of an optimal bot priority.",
        '', 'Opposing simultaneous holdings cannot be counted from entry times alone. The table has no exit timestamps or pending-order state. Alternating directions do not establish overlap. The user confirms opposing holdings are unintended: the proposed portfolio invariant is no new opposing exposure for a ticker while an existing position or pending entry remains, with exit/reduction orders still available. Test this offline using ordered order/fill events before operational adoption. Do not automatically close an existing position on a new opposite signal.',
        '', '## Exploratory entry screens',
        '', 'These screens retain actual historical rows and their unchanged reported outcomes. They are not backtests: skipping trades changes cooldowns, capital, risk locks and available subsequent signals. Every evaluated screen is retained, including failures. Thresholds are exploratory and already exposed to this data.',
        '',table({t['id']+' '+t['name']:t['retained'] for t in trials}),
        '', '### Same screens excluding flagged rows','',table({t['id']+' '+t['name']:t['retained_unflagged'] for t in trials}),
        '', 'Per-screen retained/removed IDs and complementary P&L are in experiments.csv and metrics.json. Do not combine dollar improvements across screens; their excluded trades overlap.',
        '', '## Research sequence',
        '', '1. Freeze this table and the intended configuration. Audit the direction mismatch against the actual Friday run configuration before interpreting today\'s trend-side code as Friday\'s behavior.',
        '2. Test a shared ticker-direction entry gate in disconnected replay; include pending orders, partial fills, concurrent signals and persistence. Measure same-direction duplication separately; the user has not prohibited it.',
        '3. Compare the fixed entry screens on fresh chronological sessions. Replay the complete bot state, not just retained rows. Track performance by bot and market day at comparable risk and exposure.',
        '4. Test exits only with ordered underlying paths and option quote/order data. Separate signal failure, late entry, stop overshoot and exit execution failure.',
        '5. Evaluate realistic option costs and account risk constraints, including existing stricter bot limits. The supplied table cannot reconstruct realized-plus-unrealized equity, loss-streak timing, concurrent risk, or 50–100% premium returns.',
        '', '## Reproduce and validate',
        '', '`python3 research/scalp_city/analyze.py` (Python 3 standard library; offline). Outputs are deterministic apart from environment metadata in manifest.json. Parser enforces row identity, valid outcomes and excursion signs; every partition and screen reconciles to the supplied total. No production files or broker state are changed.',
        '', 'See README.md for the source contract and decisions, experiments.json for hypotheses and failure criteria, and results/manifest.json for hashes. This baseline supplies diagnosis and candidate experiments; profitable improvements remain unproven.'
    ])
    (OUT/'report.md').write_text('\n'.join(lines)+'\n')
    manifest=dict(session='2026-10-09',timezone='America/New_York',python=platform.python_version(),
                  input=str(SOURCE.relative_to(ROOT)),sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  experiments_sha256=hashlib.sha256((ROOT/'experiments.json').read_bytes()).hexdigest(),
                  rows=52,excluded='Restart positions not present in supplied table; no additional filtering of primary sample',
                  validation='Unique ordered IDs, domains, excursion signs, partition counts/P&L and screen complements passed')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:diagnostics[k] for k in ('all','unflagged','signal_clusters','duplicate_groups')},indent=2))
    print(table({t['id']+' '+t['name']:t['retained'] for t in trials}))

if __name__=='__main__':
    main()
