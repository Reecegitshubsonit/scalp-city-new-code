"""Option-side look at the 52 closed paper trades of 2026-10-09: premiums, spreads, fill cost vs mid, how much the option moved per
underlying move (effective delta), and what is left over (time decay + noise). Read-only: event log only, no broker, no network.
Run from repo root: python3 reports/dissect-2026-10-09/option_side.py -> reports/dissect-2026-10-09/option_side.{txt,csv}"""
import csv, statistics as st, sys
sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import dissect as X
X.P = lambda *a: None
series, state, trades, failed, orphans = X.read_log()
allc = X.part1(series, state, trades, failed, orphans)
C = [c for c in allc if not c.get("orphan")]
QTY = 1000   # 10 contracts x 100
out = []
def P(s): print(s); out.append(s)
rows = []
for k, c in enumerate(C, 1):
    S = series[c["tk"]]
    mi, mo = (c["in_bid"] + c["in_ask"]) / 2, (c["out_bid"] + c["out_ask"]) / 2
    und_in, und_out = S[c["in_t"]]["p"], S[c["out_t"]]["p"]
    du = c["sgn"] * (und_out - und_in)                         # underlying move in the trade's favour, $
    dm = mo - mi                                               # option mid change, $ per share
    rows.append(dict(k=k, bot=c["bot"], tk=c["tk"], dir=c["dir"], why=c["why"], pnl=c["pnl"], hold=c["hold"], atr=c["atr"], atr_bp=c["atr_bp"],
                     mid_in=mi, mid_out=mo, spr_in=c["in_ask"] - c["in_bid"], spr_out=c["out_ask"] - c["out_bid"],
                     spr_in_pct=100 * (c["in_ask"] - c["in_bid"]) / mi, cost_in=round((c["in_px"] - mi) * QTY), cost_out=round((mo - c["out_px"]) * QTY),
                     du=du, dm=dm, R_und=du / c["atr"], delta=dm / du if abs(du) >= 0.5 * c["atr"] else None,
                     mid_pnl=round(dm * QTY), usd_per_R=None))
# per-ticker fit: mid change = delta * underlying move + decay * minutes held
P("FIT per ticker: option mid change ($/share) = delta x underlying move ($) + decay x minutes held   (least squares, closed trades)")
fit = {}
for tk in ("SPY", "QQQ", "IWM"):
    xs = [r for r in rows if r["tk"] == tk]
    a11 = sum(r["du"] ** 2 for r in xs); a12 = sum(r["du"] * r["hold"] for r in xs); a22 = sum(r["hold"] ** 2 for r in xs)
    b1 = sum(r["du"] * r["dm"] for r in xs); b2 = sum(r["hold"] * r["dm"] for r in xs)
    det = a11 * a22 - a12 ** 2; d = (b1 * a22 - b2 * a12) / det; th = (a11 * b2 - a12 * b1) / det
    res = [r["dm"] - d * r["du"] - th * r["hold"] for r in xs]
    fit[tk] = (d, th)
    P(f"  {tk}: n={len(xs):2d} delta {d:.3f}  decay {th*100:+.2f} cents/min per share (= ${th*QTY:+.1f}/min for 10 contracts)  residual sd ${st.pstdev(res)*QTY:.0f}/trade  "
      f"median premium {st.median(r['mid_in'] for r in xs):.2f}")
for r in rows:
    d, th = fit[r["tk"]]; r["usd_per_R"] = round(d * r["atr"] * QTY); r["decay_usd"] = round(th * r["hold"] * QTY); r["und_usd"] = round(d * r["du"] * QTY)
P("\nSPREAD AND FILL COST (10 contracts)")
for tk in ("SPY", "QQQ", "IWM"):
    xs = [r for r in rows if r["tk"] == tk]
    P(f"  {tk}: entry spread median ${st.median(r['spr_in'] for r in xs):.3f} ({st.median(r['spr_in_pct'] for r in xs):.2f}% of mid) = ${st.median(r['spr_in'] for r in xs)*QTY:.0f} per round trip at full width; "
      f"paid vs mid: entry {sum(r['cost_in'] for r in xs):+d}, exit {sum(r['cost_out'] for r in xs):+d} (negative = better than mid)")
P("\nWHAT 1R IS WORTH vs WHAT A TRADE COSTS (per 10-contract trade, fitted delta)")
for lab, f in (("ATR >= 5 bp", lambda r: r["atr_bp"] >= 5), ("ATR 3-5 bp", lambda r: 3 <= r["atr_bp"] < 5), ("ATR < 3 bp", lambda r: r["atr_bp"] < 3)):
    xs = [r for r in rows if f(r)]
    if not xs: continue
    spread = st.mean(r["spr_in"] / 2 + r["spr_out"] / 2 for r in xs) * QTY
    P(f"  {lab:11s} n={len(xs):2d}  1R = ${st.mean(r['usd_per_R'] for r in xs):4.0f}  half-spread in+out = ${spread:3.0f}  decay = ${-st.mean(r['decay_usd'] for r in xs):3.0f}  "
      f"-> fixed cost = {(spread - st.mean(r['decay_usd'] for r in xs)) / st.mean(r['usd_per_R'] for r in xs):.2f}R per trade")
P("\nP&L DECOMPOSITION, all 52 trades ($)")
tot = lambda k: sum(r[k] for r in rows)
P(f"  logged P&L {tot('pnl'):+.0f} = mid-to-mid {tot('mid_pnl'):+.0f}  + fills vs mid {-(tot('cost_in') + tot('cost_out')):+.0f}")
P(f"  mid-to-mid {tot('mid_pnl'):+.0f} ~ underlying move x delta {tot('und_usd'):+.0f}  + decay {tot('decay_usd'):+.0f}  + residual {tot('mid_pnl') - tot('und_usd') - tot('decay_usd'):+.0f}")
P(f"  underlying move alone: {sum(r['R_und'] for r in rows):+.1f}R across 52 trades")
P("\nPER TRADE")
P(f"  {'#':>2} {'bot':10s} {'dir':4s} {'why':6s} {'pnl':>5} {'hold':>4} {'mid in':>6} {'mid out':>7} {'spr%':>5} {'und R':>6} {'delta':>5} {'$/R':>4} {'cost in/out':>11}")
for r in rows:
    P(f"  {r['k']:2d} {r['bot']:10s} {r['dir']:4s} {r['why']:6s} {r['pnl']:+5.0f} {r['hold']:4d} {r['mid_in']:6.3f} {r['mid_out']:7.3f} {r['spr_in_pct']:5.2f} {r['R_und']:+6.2f} "
      f"{(f'{r[chr(100)+chr(101)+chr(108)+chr(116)+chr(97)]:.2f}' if r['delta'] is not None else '  -  '):>5} {r['usd_per_R']:4d} {r['cost_in']:+5d}/{r['cost_out']:+d}")
with open("reports/dissect-2026-10-09/option_side.csv", "w", newline="") as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); [w.writerow(r) for r in rows]
open("reports/dissect-2026-10-09/option_side.txt", "w").write("\n".join(out) + "\n")
