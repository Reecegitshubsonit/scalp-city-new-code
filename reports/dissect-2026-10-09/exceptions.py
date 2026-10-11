"""Oct 9 exceptions among the 49 clean trades: PUTs that hit target and CALLs that stopped, with the context at the signal.
Research only. Run from repo root: python3 reports/dissect-2026-10-09/exceptions.py -> reports/dissect-2026-10-09/exceptions.txt"""
import sys
sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import setup_puts as SP
X = SP.X
out = []
def P(s): print(s); out.append(s)
H = "  #   bot        signal  pnl   best/worst    EMA50 slope20  aboveVWAP30  prior5m(in trade dir)  vs VWAP  ATR bp  30m after exit best/worst"
def row(c):
    sl = "  n/a" if c["slope50"] is None else f"{c['slope50']:+.2f}"
    P(f"  #{c['k']:2d} {c['bot']:10s} {X.hm(c['sig_t'])}  {c['pnl']:+4.0f}  {c['mfe']:+.2f}/{c['mae']:+.2f}   {sl:>6}         {c['above_vwap_30']:4.0%}        {c['pre5']!s:>5}          "
      f"{c['vwap_side']:+5.1f}   {c['atr_bp']:4.1f}   {c['post_mfe']}/{c['post_mae']}")
for lab, f in (("PUTS THAT HIT TARGET", lambda c: c["dir"] == "PUT" and c["why"] == "TARGET"), ("PUTS THAT STOPPED", lambda c: c["dir"] == "PUT" and c["why"] == "STOP"),
               ("CALLS THAT STOPPED", lambda c: c["dir"] == "CALL" and c["why"] == "STOP"), ("CALLS THAT HIT TARGET", lambda c: c["dir"] == "CALL" and c["why"] == "TARGET")):
    xs = [c for c in SP.C if f(c)]
    P(f"\n{lab} ({len(xs)}), logged ${sum(c['pnl'] for c in xs):+.0f}"); P(H); [row(c) for c in xs]
    num = lambda k: [c[k] for c in xs if c[k] is not None]
    avg = lambda v: sum(v) / len(v) if v else float("nan")
    P(f"  averages: prior5m {avg(num('pre5')):+.2f}  vs VWAP {avg(num('vwap_side')):+.2f}  aboveVWAP30 {avg(num('above_vwap_30')):.0%}  EMA50 slope {avg(num('slope50')):+.2f}  ATR {avg(num('atr_bp')):.1f} bp  hold {avg(num('hold')):.0f}m")
open("reports/dissect-2026-10-09/exceptions.txt", "w").write("\n".join(out) + "\n")
