"""Audit and diagnose the expanded Friday log-derived sample. Offline, stdlib only."""
from pathlib import Path
from collections import defaultdict, Counter
from decimal import Decimal as D
import csv
import hashlib
import json
import re
import analyze as baseline

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/expanded'
OUT=ROOT/'results'
REPO=ROOT.parents[1]


def read(name):
    with (DATA/name).open(newline='') as f:
        return list(csv.DictReader(f))


def minute(s):
    h,m=map(int,s.split(':')); return h*60+m


def d(row,key):
    return D(row[key])


def summary(rows):
    return dict(n=len(rows), ids=[int(r['n']) for r in rows],
                logged=sum(float(r['pnl_logged']) for r in rows),
                mids=sum(float(r['pnl_at_mids']) for r in rows),
                buy_ask_sell_bid=sum(float((d(r,'exit_bid')-d(r,'entry_ask'))*d(r,'qty_filled_entry')*100) for r in rows))


def table(groups):
    lines=['| Population | Trades | Logged paper P&L | Midpoint benchmark | Buy-ask/sell-bid benchmark |',
           '|---|---:|---:|---:|---:|']
    for label,rows in groups.items():
        s=summary(rows)
        lines.append(f"| {label} | {s['n']} | ${s['logged']:+,.0f} | ${s['mids']:+,.0f} | ${s['buy_ask_sell_bid']:+,.0f} |")
    return '\n'.join(lines)


def main():
    rows=read('trades_expanded.csv'); paths=read('price_paths.csv'); issues=read('orders_issues.csv')
    old={r['id']:r for r in baseline.read_rows()}
    assert len(rows)==52 and len(paths)==622 and len(issues)==11
    assert len({r['trade_id'] for r in rows})==52
    assert {int(r['n']) for r in rows}==set(old)
    log_path=REPO/'logs/2026-10-09-live.jsonl'
    events=[json.loads(s) for s in log_path.read_text().splitlines()]
    byseq={e['seq']:e for e in events}
    assert len(byseq)==len(events)
    logged_bars=defaultdict(list)
    for e in events:
        if e['kind']=='tick' and e['inputs'].get('price') is not None:
            logged_bars[(e['ticker'],e['time'][11:16])].append(e['inputs'])
    paths_by_id=defaultdict(list)
    for p in paths:
        paths_by_id[p['trade_id']].append(p)
    for r in rows:
        o=old[int(r['n'])]
        assert r['bot']==o['bot'] and d(r,'pnl_logged')==o['pnl'] and r['side']==o['side']
        assert r['signal_time']==o['time'] and abs(d(r,'signal_und_close')-D(str(o['price'])))<=D('.0051')
        assert r['qty_ordered']==r['qty_filled_entry']==r['qty_filled_exit']=='10'
        for prefix,reason in [('entry','ENTRY_FILL'),('exit','EXIT_FILL')]:
            e=byseq[int(r[f'{prefix}_fill_seq'])]
            assert e['kind']=='fill' and e['reason_code']==reason and e['bot']==r['bot']
            assert e['contract']==r['option_symbol'] and D(str(e['fill_price']))==d(r,f'{prefix}_fill_price')
            assert e['time'][11:16]==r[f'{prefix}_fill_time'] and e['qty']==10
        sig=byseq[int(r['signal_seq'])]
        assert sig['reason_code']=='SIGNAL' and sig['bot']==r['bot']
        assert D(str(sig['inputs']['price']))==d(r,'signal_und_close')
        assert (d(r,'exit_fill_price')-d(r,'entry_fill_price'))*d(r,'qty_filled_entry')*100==d(r,'pnl_logged')
        mid=((d(r,'exit_bid')+d(r,'exit_ask'))-(d(r,'entry_bid')+d(r,'entry_ask')))/2*100*d(r,'qty_filled_entry')
        assert abs(mid-d(r,'pnl_at_mids'))<D('.001')
        sg=1 if r['side']=='CALL' else -1
        for key,value in [('stop_und_reconstructed',d(r,'signal_und_close')-sg*d(r,'atr_at_signal')),
                          ('target_und_reconstructed',d(r,'signal_und_close')+2*sg*d(r,'atr_at_signal'))]:
            assert abs(d(r,key)-value)<=D('.0001')
            logged=key.replace('reconstructed','logged')
            if r[logged]: assert abs(d(r,logged)-value)<=D('.0051')  # display rounded to cents
        ps=paths_by_id[r['trade_id']]
        assert [p['minute'] for p in ps]==sorted({p['minute'] for p in ps})
        assert ps[0]['minute']==r['signal_time'] and ps[-1]['minute']==r['exit_fill_time']
        for p in ps:
            assert p['n']==r['n']
            assert any(all(D(str(bar[k]))==d(p,col) for k,col in [('price','und_close'),('vwap','vwap'),('ema9','ema9'),('ema21','ema21'),('ema50','ema50'),('atr','atr')]) for bar in logged_bars[(r['ticker'],p['minute'])])
            expected=sg*(d(p,'und_close')-d(r,'signal_und_close'))/d(r,'atr_at_signal')
            assert abs(expected-d(p,'move_R'))<=D('.00051')
        assert minute(r['exit_fill_time'])-minute(r['entry_fill_time'])==int(r['hold_min'])
    assert sum(int(r['exit_retries']) for r in rows)==sum(i['kind']=='EXIT_RETRY' for i in issues)==6

    pairs=[]; same=[]
    for index,a in enumerate(rows):
        for b in rows[index+1:]:
            if a['ticker']!=b['ticker'] or a['bot']==b['bot']:continue
            start=max(a['entry_fill_time'],b['entry_fill_time']); end=min(a['exit_fill_time'],b['exit_fill_time'])
            if start<end:
                pair=dict(a=int(a['n']),b=int(b['n']),ticker=a['ticker'],start=start,end=end,minutes=minute(end)-minute(start))
                (pairs if a['side']!=b['side'] else same).append(pair)
    opposing_ids={x[k] for x in pairs for k in ('a','b')}
    same_ids={x[k] for x in same for k in ('a','b')}
    graph=defaultdict(set)
    for p in pairs:graph[p['a']].add(p['b']);graph[p['b']].add(p['a'])
    components=[];todo=set(graph)
    while todo:
        stack=[min(todo)]; comp=set()
        while stack:
            n=stack.pop()
            if n in comp:continue
            comp.add(n);stack.extend(graph[n]-comp)
        todo-=comp;components.append(sorted(comp))
    for r in rows:
        supplied={int(n) for n in re.findall(r'#(\d+)',r['opposing_overlap'])}
        assert supplied==graph[int(r['n'])]
    # Policy sensitivity restricted to these historical entries; existing retained exits remain fixed.
    kept=[];blocked=[]
    for r in sorted(rows,key=lambda r:int(r['entry_fill_seq'])):
        conflicts=[p for p in kept if p['ticker']==r['ticker'] and p['side']!=r['side'] and int(p['exit_fill_seq'])>int(r['entry_fill_seq'])]
        if conflicts:blocked.append(dict(n=int(r['n']),blocked_by=[int(p['n']) for p in conflicts]))
        else:kept.append(r)
    blocked_ids={p['n'] for p in blocked}
    blocked_rows=[r for r in rows if int(r['n']) in blocked_ids]
    assert len(kept)+len(blocked_rows)==52
    assert summary(kept)['logged']+summary(blocked_rows)['logged']==-2270

    cross=[]
    for r in rows:
        if r['trigger'] not in ('VWAP','EMA50'):continue
        sig=byseq[int(r['signal_seq'])]; field='vwap' if r['trigger']=='VWAP' else 'ema50'
        previous=[e for e in events if e['bot']==r['bot'] and e['kind']=='tick' and e['seq']<sig['seq']]
        prior=previous[-1]['inputs'] if previous else None
        now=sig['inputs']; direction=None
        if prior:
            if prior['price']<prior[field] and now['price']>now[field]:direction='CALL'
            if prior['price']>prior[field] and now['price']<now[field]:direction='PUT'
        cross.append(dict(n=int(r['n']),observed=direction,side=r['side'],matches=direction==r['side']))

    exit_diagnostics=[]
    for r in rows:
        ps=paths_by_id[r['trade_id']]
        sg=1 if r['side']=='CALL' else -1
        def move(p):return sg*(d(p,'und_close')-d(r,'signal_und_close'))/d(r,'atr_at_signal')
        after=[p for p in ps if p['minute']>r['signal_time']]
        hit1=next((p['minute'] for p in after if move(p)>=1),None)
        hitstop=next((p['minute'] for p in after if move(p)<=-1),None)
        hit2=next((p['minute'] for p in after if move(p)>=2),None)
        seq0=int(r['entry_fill_seq']); seq1=int(r['exit_fill_seq'])
        exits=[e for e in events if seq0<e['seq']<seq1 and e['bot']==r['bot'] and e['kind']=='state_change' and e['reason_code'] in ('EXIT_TARGET','EXIT_STOP')]
        exit_diagnostics.append(dict(n=int(r['n']),first_trigger=r['exit_trigger'],final_result=old[int(r['n'])]['result'],
            first_plus1=hit1,first_minus1=hitstop,first_plus2=hit2,
            plus1_before_stop=bool(hit1 and (not hitstop or hit1<hitstop)),
            exit_underlying_atr=float(r['exit_R_und']),
            trigger_to_fill_bar_minutes=minute(r['exit_fill_time'])-minute(r['exit_trigger_time']),
            missing_path_minutes=int(r['hold_min'])+1-len(ps),
            exit_events=[dict(seq=e['seq'],time=e['time'][11:16],reason=e['reason_code']) for e in exits]))
    stops=[x for x in exit_diagnostics if x['final_result']=='stop']
    early=[x['n'] for x in stops if x['plus1_before_stop']]
    overshoot=[x for x in stops if x['exit_underlying_atr']<-1]
    retry_rows=[r for r in rows if int(r['exit_retries'])]
    # Reuse the frozen six hypotheses on the same row memberships; no threshold retuning.
    base_metrics=json.loads((OUT/'metrics.json').read_text())
    screens={t['id']+' '+t['name']:[r for r in rows if int(r['n']) in t['retained']['ids']] for t in base_metrics['experiments']}
    results=dict(baseline=summary(rows),opposing_pairs=pairs,opposing_components=components,
        opposing=summary([r for r in rows if int(r['n']) in opposing_ids]),
        same_side_pairs=same,same_side_trade_count=len(same_ids),
        no_opposing_sensitivity=dict(retained=summary(kept),blocked=summary(blocked_rows),decisions=blocked),
        side_cross_checks=cross,exit_diagnostics=exit_diagnostics,
        stops_reached_plus1_before_minus1=early,stop_exit_overshoot_count=len(overshoot),
        stop_exit_overshoot_atr_sum=sum(-1-x['exit_underlying_atr'] for x in overshoot),
        screens={k:summary(v) for k,v in screens.items()})
    (OUT/'expanded_metrics.json').write_text(json.dumps(results,indent=2)+'\n')
    with (OUT/'opposing_pairs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
    with (OUT/'exit_diagnostics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(exit_diagnostics[0]));w.writeheader();w.writerows(exit_diagnostics)
    lines=['# Expanded Friday paper-trade investigation',
        '', 'Actual paper session: October 9, 2026. All 52 original closed trades retained; the three excluded restart positions remain out of scope. This report supersedes the original report’s missing-timeline limitations. Dollar results describe this selected sample, not complete account performance.',
        '', '## Conclusions',
        '', 'There are both strategy-selection weaknesses and execution/control defects. Fixing opposing holdings is required by the intended behavior, but does not by itself establish profitability. Friday followed cross directions rather than the currently intended EMA9/EMA21 side rule. The existing six screens do not become convincing after replacing logged fill prices with order-quote benchmarks.',
        '', '## Reconciliation and provenance',
        '', 'All 52 row numbers, bots, sides, signal times and logged P&L match; signal prices match within cent-display rounding against the supplied table. All 104 fill records match their raw log sequence IDs, contract, quantity, fill price and minute. Recomputed fill P&L and quote-mid P&L match every row. All 622 path rows match raw-log bar values and pass ordering and ATR-movement arithmetic checks. The 47 displayed stop/target pairs match reconstructed values within cent-display rounding; they are not literally equal at full precision.',
        '', 'CSV copies are frozen in data/expanded; the originals are unchanged. The raw log is used only for verification and ordered event evidence for these 52 trades. Raw-log mode labels are not used to reclassify the user-confirmed paper session as real-money trading.',
        '', '## Paper fills versus execution benchmarks','',table({'All 52':rows,'Originally starred #2/#4/#5':[r for r in rows if int(r['n']) in (2,4,5)],'Rebooked #7/#8':[r for r in rows if int(r['n']) in (7,8)]}),
        '', 'Logged P&L is the application’s paper-trade ledger. Quote mids are a sensitivity benchmark, not corrected actual fills. Buy-ask/sell-bid uses the entry order quote and the final exit order quote, with the observed quantity, and is also hypothetical. These quotes are timestamped by bar minute; their true age and wall-clock fill timing are unknown. None of these figures includes unlogged fees, market impact or uncertain quote/fill latency. Mids may overstate achievable results; ask/bid is not a guaranteed worst case.',
        '', 'Rows #7/#8 carry broker_offmarket fill sources: application booking may differ from broker-account prices. This is still actual paper trading, but the log alone cannot establish reconciled broker-account P&L. Do not infer broker positions from an order whose outcome is missing.',
        '', '## Actual contract and direction behavior',
        '', 'Every recorded option symbol expires October 12, 2026: these were Monday-expiring contracts traded Friday, not same-day-expiring contracts. That matters for option-price response; underlying ATR return is not option-premium return. Symbols alone do not establish that the chosen strike was the closest available ATM strike.',
        '', f"Prior/current logged indicator snapshots confirm cross-direction agreement for {sum(x['matches'] for x in cross)}/{len(cross)} VWAP/EMA50 entries. {sum(not x['ema_agrees'] for x in old.values())}/52 entries oppose their signal-time EMA9/EMA21 direction. This supports a Friday raw-cross baseline. The exact startup configuration and claimed 15:16 code-change time are not authenticated by these CSVs; some settings evidence is hard-coded by the exporter.",
        '', '## Opposing positions','',f"Verified {len(pairs)} opposing position pairs involving {len(opposing_ids)} distinct trades, grouped into {len(components)} connected sets: {components}. The supplied README’s ‘8 groups’ is inconsistent with the independently computed pair and component counts. Same-side overlap involves {len(same_ids)} trades across {len(same)} pairs. Overlap is measured from fill bar-minute intervals; same-minute details require sequence ordering, and these are not wall-clock durations.",
        '',table({'Trades involved in opposing overlap':[r for r in rows if int(r['n']) in opposing_ids],
                  'No-opposing historical-entry sensitivity: retained':kept,
                  'No-opposing historical-entry sensitivity: blocked':blocked_rows}),
        '',f"Sensitivity rule: process logged entry-fill sequence order; reject a later opposite-side entry while an earlier retained same-ticker position remains open; preserve retained original exits. Blocked IDs: {sorted(blocked_ids)}. This respects the user’s intended direction constraint but is not a full replay. It omits missing/rejected candidate signals, pending-entry states, altered cooldowns and account risk locks. Its dollar difference is not proven avoidable loss. Same-side duplication remains allowed.",
        '', '## Ordered exit evidence',
        '', f"{len(early)} of the 37 final STOP trades first reached +1 ATR on an observed close before the first observed -1 ATR close: {early}. This resolves the ordering ambiguity in the initial table, but missing minutes and lack of option quotes at hypothetical exits still prevent a validated option-P&L result for a +1 ATR target.",
        '', f"All {len(overshoot)} final STOP trades exited with underlying movement below -1 signal ATR; summed excess beyond -1 across those trades is {results['stop_exit_overshoot_atr_sum']:.3f} ATR units. This sum is a trade-normalized diagnostic, not portfolio R, dollars, or pure execution slippage. Bar-close evaluation, gaps and retries can all contribute. The 1 ATR stop was a close-based trigger, not a guaranteed fill level.",
        '', 'Trade #29: first exit trigger TARGET at 11:58, an EXIT_RETRY, then a STOP outcome at 12:01 for -$310 logged. The expanded exit_trigger column means first trigger; the original result means final outcome. It is not a row mismatch. The raw event sequence is saved in exit_diagnostics.csv. This is direct evidence for preserving a pending exit decision through retries, subject to valid executable orders.',
        '',f"Six trades have an exit retry: {[int(r['n']) for r in retry_rows]}. Trade #16 spans 13 bar minutes from target trigger to fill and finishes profitable. A retry does not automatically mean it caused a loss. Trades #18/#21 exit at -2.582/-3.154 underlying ATR after the 11:09–11:16 missing-event interval. The log establishes a gap, not its cause or what could have filled inside it.",
        '', '## Original screens under quote benchmarks','',table(screens),
        '', 'These are the same frozen six exploratory screens and retained IDs as the initial research, with no parameter tuning. Filtering actual rows is not a strategy rerun. Compare both average outcomes and exposure before declaring improvement; skipping losers discovered after the fact is not evidence of a tradable rule.',
        '', '## Export corrections and unresolved fields',
        '', '- Use 10 opposing pairs / 16 trades / 6 connected sets, with the unit stated explicitly.',
        '- stop_und_logged and target_und_logged are cent-rounded displays; use rounding tolerance, not an exact-match claim.',
        '- settings_used.csv contains hard-coded claims derived partly from code or inference, despite its log-only framing. Treat exact version/change time, threshold values and flat cutoff accordingly.',
        '- The post-restart daily-loss evidence includes an unlocked -$780 and a locked -$960. Under a shared fixed loss threshold with inclusive locking, this implies a threshold greater than $780 and at most $960, not the exported $720 lower bound. Per-bot or changing limits would invalidate that shared-threshold inference.',
        '- A +$490 unlocked observation implies a shared inclusive goal threshold greater than $490, not merely the exported $310. Before-restart observations do not establish the exported $130 lower bound.',
        '- Fee values, actual submitted limit prices and execution wall-clock timestamps are missing. Order quotes do not prove limit prices; current code is not a versioned Friday order record.',
        '- One entry order has no logged outcome. Treat it as unresolved; no broker-account quantity or fill can be established from that absence.',
        '', '## Next reproducible experiments',
        '', '1. Reproduce Friday with raw-cross direction and actual Monday expiry. Keep a separate EMA-direction variant; do not silently replace the historical baseline.',
        '2. Test the no-opposing-entry invariant at shared ticker scope with atomic pending-order reservations and position reconciliation. Preserve exits and do not automatically flip existing positions.',
        '3. Test persistent exit intent through retries and gap handling in disconnected event replay; distinguish exit-trigger price, order price and fill price.',
        '4. Compare entry and exit variants on new chronological sessions with option quotes, fees and portfolio limits. All already-examined Friday outcomes and historical trials remain development evidence.',
        '', 'Run `python3 research/scalp_city/analyze.py` then `python3 research/scalp_city/analyze_expanded.py`. All source hashes and validation counts are in expanded_manifest.json. No broker calls or production mutations are performed.'
    ]
    (OUT/'expanded_report.md').write_text('\n'.join(lines)+'\n')
    sources=[*sorted(DATA.iterdir()),log_path,Path(__file__),ROOT/'analyze.py',ROOT/'data/friday_2026-10-09.tsv',ROOT/'experiments.json']
    manifest=dict(inputs={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  verified=dict(trades=52,fill_records=104,path_rows=622,order_issues=11),
                  scope='52 supplied closed trades; excluded restart positions remain out of scope')
    (OUT/'expanded_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:results[k] for k in ['baseline','opposing_components','no_opposing_sensitivity','stops_reached_plus1_before_minus1','stop_exit_overshoot_atr_sum']},indent=2))
    print('Cross-direction verified',sum(x['matches'] for x in cross),len(cross))
    print(table(screens))

if __name__=='__main__':main()
