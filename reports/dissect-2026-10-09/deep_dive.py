"""Per-trade deep dive for 2026-10-09: the trade's data, then a written breakdown from its minute-by-minute path.
Research only. Run from repo root: python3 reports/dissect-2026-10-09/deep_dive.py -> reports/dissect-2026-10-09/deep_dive.md"""
import json, sys
sys.path.insert(0, "reports/dissect-2026-10-09"); sys.argv = ["x"]
import dissect as X
X.P = lambda *a: None
series, state, trades, failed, orphans = X.read_log()
allc = X.part1(series, state, trades, failed, orphans)
ev = [json.loads(l) for l in open(X.LOG)]
TRIG = {"VWAP": "price closed across VWAP", "EMA50": "price closed across EMA50", "RANGE": "price closed outside the 9:30-9:44 range"}
V = {"t1": dict(stop=1, tgt=1), "be": dict(stop=1, tgt=2, be=1), "t10": dict(stop=1, tgt=2, tmax=10)}
res = {k: X.replay_today(allc, series, v) for k, v in V.items()}
def hm(x): return f"{x//60:02d}:{x%60:02d}"
def others(c):
    """Other bots holding the same ticker at this entry."""
    o = []
    for d in allc:
        if d is c or d["tk"] != c["tk"] or d.get("orphan"): continue
        if d["in_t"] <= c["in_t"] <= d.get("out_t", 999): o.append(f"{d['bot']} {d['dir']}")
    return o
def side_replay(c, d):
    S = series[c["tk"]]; v = dict(stop=1, tgt=2)
    p = X.open_pos(d, c["sig_px"], c["atr"], v, None, 0); R = 0
    for t in range(c["sig_t"] + 1, 960):
        if t not in S: continue
        p["held"] += 1; why, R = X.exit_check(p, S[t]["p"], X.T(t // 60, t % 60), v)
        if why: break
    return d, R
def vwap_side_replay(c):
    S = series[c["tk"]]; d = "CALL" if c["sig_px"] > c["vwap"] else "PUT"; v = dict(stop=1, tgt=2)
    p = X.open_pos(d, c["sig_px"], c["atr"], v, None, 0); R = 0
    for t in range(c["sig_t"] + 1, 960):
        if t not in S: continue
        p["held"] += 1; why, R = X.exit_check(p, S[t]["p"], X.T(t // 60, t % 60), v)
        if why: break
    return d, R
L = ["# 2026-10-09 deep dive, all 52 closed trades", "",
     "R = 1 ATR = stop distance. Move = underlying close minus signal close, in signal ATR, + = trade's favour. Stop -1R, target +2R on a bar close.", ""]
n = 0
for i, c in enumerate(allc):
    if c.get("orphan"): continue
    n += 1
    S, s, a, p0 = series[c["tk"]], c["sgn"], c["atr"], c["sig_px"]
    mv = {t: s * (S[t]["p"] - p0) / a for t in range(c["sig_t"], c["out_t"] + 31) if t in S}
    hold = [t for t in mv if c["sig_t"] < t <= c["out_t"]]
    peak_t = max(hold, key=lambda t: mv[t]) if hold else c["sig_t"]
    low_t = min(hold, key=lambda t: mv[t]) if hold else c["sig_t"]
    first_up = next((t for t in hold if mv[t] >= 1), None)
    first_neg = next((t for t in hold if mv[t] < 0), None)
    post = [t for t in mv if t > c["out_t"]]
    post_peak = max(post, key=lambda t: mv[t]) if post else None
    mid_in = (c["in_bid"] + c["in_ask"]) / 2; mid_out = (c["out_bid"] + c["out_ask"]) / 2
    oth = others(c)
    tr = c["trig"]; trend = "EMA9 above EMA21" if c["e9"] > c["e21"] else "EMA9 below EMA21"
    # header + data
    L.append(f"### {n}. {c['bot']} {c['dir']} {c['contract']}: {c['pnl']:+.0f} ({c['why'].lower()})")
    L.append("")
    L.append(f"Signal {hm(c['sig_t'])} @ {p0:.2f} · in {c['in_px']:.2f} (q {c['in_bid']}/{c['in_ask']}) · stop {c['stop']:.2f} / tgt {c['target']:.2f} · ATR {a:.3f} ({c['atr_bp']} bp) · "
             f"out {hm(c['out_t'])} {c['out_px']:.2f} (q {c['out_bid']}/{c['out_ask']}) at {c['out_R']:+.2f}R · {c['hold']}m · best {c['mfe']:+.2f} / worst {c['mae']:+.2f}")
    L.append("")
    # breakdown
    B = []
    agree = (c["e9"] > c["e21"]) == (c["dir"] == "CALL")
    side_txt = ("break direction" if tr == "RANGE" else "cross direction") + f" ({c['dir']}); EMA9/21 {'agreed' if agree else 'pointed the other way'}"
    B.append(f"**Setup.** {TRIG.get(tr, tr)}; side = {side_txt}. "
             f"VWAP {c['vwap_side']:+.1f} ATR, EMA50 {c['e50_side']:+.1f} ATR (+ = on trade's side). "
             + (f"Prior 5 min {c['pre5']:+.1f} ATR{' = chasing' if c['pre5'] >= 1 else ''}. " if c['pre5'] is not None else "")
             + (f"ATR only {c['atr_bp']} bp, stop {a:.2f} wide. " if c['atr_bp'] < 3 else "")
             + (f"Also open on {c['tk']}: {', '.join(oth)}." if oth else ""))
    path = f"**Path.** "
    if c["mfe"] <= 0.05: path += f"Never moved in its favour. "
    else: path += f"Best {mv[peak_t]:+.2f}R at {hm(peak_t)}" + (f" (passed +1R at {hm(first_up)})" if first_up else "") + ". "
    if first_neg and c["why"] == "STOP": path += f"Below entry from {hm(first_neg)}. "
    path += f"Worst close {mv[low_t]:+.2f}R at {hm(low_t)}. "
    if c["why"] == "STOP":
        path += f"Stop triggered on the {hm(c['exit_sig_t'])} close ({mv.get(c['exit_sig_t'], 0):+.2f}R)"
        path += (f", exit failed {c['retries']}x, " if c['retries'] else ", ") + f"filled {hm(c['out_t'])} at {c['out_R']:+.2f}R"
        path += f" ({abs(c['out_R']) - 1:.2f}R past the stop line)." if c["out_R"] < -1.05 else "."
    else:
        path += f"Target triggered on the {hm(c['exit_sig_t'])} close, filled {hm(c['out_t'])} at {c['out_R']:+.2f}R."
    B.append(path)
    fills = None and f" {c['in_px']:.2f} vs mid {mid_in:.3f}, sold {c['out_px']:.2f} vs mid {mid_out:.3f}."
    if not (c["in_bid"] - .011 <= c["in_px"] <= c["in_ask"] + .011) or not (c["out_bid"] - .011 <= c["out_px"] <= c["out_ask"] + .011):
        B.append(f"**Fills.** Fill outside quote: logged {c['pnl']:+.0f} not real; at mids {(mid_out - mid_in) * 1000:+.0f}.")
    if post_peak is not None:
        B.append(f"**After exit (30 min).** Best {mv[post_peak]:+.2f}R at {hm(post_peak)}, worst {min(mv[t] for t in post):+.2f}R. "
                 + ("Price reached the target after the stop: direction right, stop too tight for the noise." if c["post_target"] and c["why"] == "STOP" else
                    "Kept going the trade's way after the target." if c["why"] == "TARGET" and mv[post_peak] > 2.5 else
                    "Reversed after the target; exit timing was good." if c["why"] == "TARGET" else
                    "Kept going against the trade; the stop saved a bigger loss." if min(mv[t] for t in post) < -1.5 else "Drifted; no clear follow-through either way."))
    vd, vR = vwap_side_replay(c)
    r = {k: res[k][i]["R"] for k in V}
    if c["why"] == "TARGET":
        verdict = "Worked as designed."
        diff = "Nothing to change on this trade. " + ("Against VWAP; a VWAP-side rule would have flipped this winner." if vd != c["dir"] else "")
    else:
        why = {"CHOPPED OUT": "chopped out: small favour, then stopped", "WRONG SIDE FROM THE START": "wrong side from the first minute",
               "CHASED AN EXTENDED MOVE": "chased a move that was already done", "GAVE BACK A 1R+ GAIN": "had 1R+ profit and gave it all back",
               "RIGHT SIDE, STOPPED FIRST": "right direction, stopped out by noise first"}[c["label"]]
        verdict = why[0].upper() + why[1:] + "."
        o = []
        if r["t1"] > 0: o.append(f"1R target {r['t1']:+.1f}R")
        if vd != c["dir"]: o.append(f"VWAP side ({vd}) {vR:+.1f}R")
        td, tR = side_replay(c, "CALL" if c["e9"] > c["e21"] else "PUT")
        if td != c["dir"]: o.append(f"EMA9/21 side ({td}) {tR:+.1f}R")
        if r["t10"] > c["out_R"] + 0.3: o.append(f"10 min time stop {r['t10']:+.1f}R")
        if c["out_R"] < -1.25: o.append(f"fill at stop line saves {abs(c['out_R']) - 1:.2f}R")
        if c["retries"]: o.append("the exit order must not fail")
        if "REENTRY" in str(c.get("tags")): pass
        diff = ("Different: " + "; ".join(o) + ".") if o else "Different: no tested rule saves it."
    B.append(f"**Verdict.** {verdict} {diff}")
    L += B + [""]
open("reports/dissect-2026-10-09/deep_dive.md", "w").write("\n".join(L) + "\n")
print(n)
