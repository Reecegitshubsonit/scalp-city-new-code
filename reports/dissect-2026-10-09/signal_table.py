"""One row per Oct 9 trade with every trigger's state at the signal minute. Read-only, event log only.
Opening range (9:30-9:44 high/low) is not logged; it is recovered from the RANGE bots' 'distance to trigger' ticks
(close +/- distance x ATR clusters on one high and one low per ticker) and checked against every RANGE signal.
Run from repo root: python3 reports/dissect-2026-10-09/signal_table.py -> reports/dissect-2026-10-09/signal_table.{md,csv}"""
import collections, csv, json, sys
sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import setup_puts as SP
X = SP.X
cand = collections.defaultdict(collections.Counter)
for l in open(X.LOG):
    d = json.loads(l)
    if d["kind"] == "tick" and d["bot"].endswith("RANGE") and d["reason_code"] == "WATCHING" and d["inputs"].get("distance_atr"):
        i = d["inputs"]
        for v in (i["price"] + i["distance_atr"] * i["atr"], i["price"] - i["distance_atr"] * i["atr"]): cand[d["ticker"]][round(v, 2)] += 1
RNG = {tk: tuple(sorted(v for v, _ in c.most_common(2))) for tk, c in cand.items()}
for c in SP.F.C:
    if not hasattr(c, "get") or "slope50" not in c: SP.ctx(c)
rows = []
for c in SP.F.C:
    a, p = c["atr"], c["sig_px"]; lo, hi = RNG[c["tk"]]
    gap = abs(c["e9"] - c["e21"]) / a
    rows.append(dict(
        n=c["k"], bot=c["bot"], side=c["dir"], signal=X.hm(c["sig_t"]), price=round(p, 2), pnl=int(c["pnl"]), result=c["why"], flag="off-market fill" if c["k"] in (2, 4, 5) else "",
        atr=round(a, 3), atr_bp=c["atr_bp"],
        vwap=f"{'above' if p > c['vwap'] else 'below'} {abs(p - c['vwap']) / a:.1f}",
        ema50=f"{'above' if p > c['e50'] else 'below'} {abs(p - c['e50']) / a:.1f}",
        slope50="n/a" if c["slope50"] is None else f"{'up' if c['slope50'] > 0 else 'down'} {abs(c['slope50']):.1f}",
        range="above" if p > hi else "below" if p < lo else "inside",
        ema9_21=f"{'9>21' if c['e9'] > c['e21'] else '9<21'} {gap:.2f}" + (" SQUEEZE" if gap < 0.15 else ""),
        above_vwap30=f"{c['above_vwap_30']:.0%}", run5=c["pre5"], best=c["mfe"], worst=c["mae"],
        after30=f"{c['post_mfe']}/{c['post_mae']}"))
cols = list(rows[0])
with open("reports/dissect-2026-10-09/signal_table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); [w.writerow(r) for r in rows]
hdr = "| # | bot | side | signal | P&L | result | ATR (bp) | VWAP | EMA50 | EMA50 slope | range | EMA9/21 | above VWAP 30m | run before | best/worst | 30m after exit |"
L = [f"Opening range 9:30-9:44: " + ", ".join(f"{tk} {lo:.2f}-{hi:.2f}" for tk, (lo, hi) in sorted(RNG.items())), "", hdr, "|" + "---|" * 16]
for r in rows:
    L.append(f"| {r['n']}{'*' if r['flag'] else ''} | {r['bot']} | {r['side']} | {r['signal']} @ {r['price']} | {r['pnl']:+d} | {r['result'].lower()} | {r['atr']:.3f} ({r['atr_bp']}) | {r['vwap']} | {r['ema50']} | {r['slope50']} | {r['range']} | {r['ema9_21']} | {r['above_vwap30']} | {r['run5'] if r['run5'] is not None else 'n/a'} | {r['best']:+.2f}/{r['worst']:+.2f} | {r['after30']} |")
open("reports/dissect-2026-10-09/signal_table.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
