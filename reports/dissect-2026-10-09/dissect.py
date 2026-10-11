"""Minute-by-minute dissection of the 2026-10-09 paper day, plus an exit-rule study that keeps the same entries.
Research only: reads logs/2026-10-09-live.jsonl and backtest/data, no network, no broker, no .env.
Run from repo root:  python3 reports/dissect-2026-10-09/dissect.py
Writes reports/dissect-2026-10-09/{timeline.csv, trades.md, features.csv, variants.csv, output.txt}.

Part 1  every call from the log, minute by minute (signal-5 .. exit+15), with a failure label per trade.
Part 2  entry-time features of winners vs losers, today and over 90 historical days (same live rules).
Part 3  exit variants on the SAME entries: today's actual signals and 90 days split train / validation / holdout.
        Historical simulator mirrors live: cross/range trigger, side from EMA9 vs EMA21 (trend_side=True),
        chop skip on the VWAP bot only, bar-close stop/target, 2 min cooldown, entries 9:30-15:30 (range from 9:45), flat 15:55.
        Option dollars use the premium/theta model from reports/analysis-2026-10-09/analyze.py, with spread per ticker
        set to today's quoted median (SPY 0.52%, QQQ 0.41%, IWM 1.47% of mid) and a 2% pessimistic case.
"""
import collections, csv, json, math, os, re, statistics as st, sys
from datetime import datetime, time as T, timedelta

sys.path.insert(0, "reports/analysis-2026-10-09")
import analyze as A   # load, prepare, premium_model, tmin, constants

OUT = "reports/dissect-2026-10-09/"
LOG = "logs/2026-10-09-live.jsonl"
BA = re.compile(r"bid/ask ([\d.]+)/([\d.]+)")
LIVE_SPREAD = {"SPY": 0.0052, "QQQ": 0.0041, "IWM": 0.0147}
lines = []


def P(*a):
    s = " ".join(str(x) for x in a); print(s); lines.append(s)


def mins(s): h, m = s.split(":"); return int(h) * 60 + int(m)
def hm(x): return f"{x // 60:02d}:{x % 60:02d}"


# ======================= Part 1: today's log =======================
def read_log():
    ev = [json.loads(l) for l in open(LOG)]
    series = collections.defaultdict(dict)            # ticker -> minute -> indicators
    state = collections.defaultdict(dict)             # bot -> minute -> (state, reason)
    for d in ev:
        i = d.get("inputs") or {}
        if d["kind"] == "tick":
            state[d["bot"]][mins(d["time"][11:16])] = (d["state"], d["reason_code"])
            if i.get("price") is not None:
                series[d["ticker"]][mins(d["time"][11:16])] = dict(p=i["price"], vwap=i.get("vwap"), e9=i.get("ema9"), e21=i.get("ema21"), e50=i.get("ema50"), atr=i.get("atr"))
    cur, trades, failed, orphans = {}, [], [], []
    for d in ev:
        b, k, r, tm = d["bot"], d["kind"], d["reason_code"], mins(d["time"][11:16])
        i = d.get("inputs") or {}
        c = cur.get(b)
        if k == "state_change" and r == "SIGNAL":
            if c and c.get("in_t") is not None:
                c["orphan"] = True; orphans.append(c)
            cur[b] = c = dict(bot=b, tk=d["ticker"], trig=b.split("-")[1], sig_t=tm, sig_px=i["price"], atr=i["atr"], vwap=i.get("vwap"),
                              e9=i.get("ema9"), e21=i.get("ema21"), e50=i.get("ema50"), charge=d.get("charge_pct"), events=[(tm, "SIGNAL")], retries=0)
        elif not c:
            continue
        elif k == "order_sent" and r == "BUY_OPEN":
            m = BA.search(d["reason_text"]); con = d["contract"]
            c.update(contract=con, dir="CALL" if con[len(d["ticker"]) + 6] == "C" else "PUT", in_bid=float(m[1]), in_ask=float(m[2]))
            c["sgn"] = 1 if c["dir"] == "CALL" else -1
        elif k == "state_change" and r == "ORDER_FAILED" and "in_t" not in c:
            c["events"].append((tm, "ENTRY NOT FILLED")); failed.append(c); cur.pop(b, None)
        elif k == "fill" and r == "ENTRY_FILL":
            c.update(in_t=tm, in_px=d["fill_price"]); c["events"].append((tm, f"BOUGHT {d['fill_price']:.2f}"))
        elif k == "state_change" and r.startswith("EXIT_"):
            if r == "EXIT_RETRY": c["retries"] += 1; c["events"].append((tm, "EXIT NOT FILLED, RETRY"))
            else: c.update(why=r[5:], exit_sig_t=tm); c["events"].append((tm, f"EXIT {r[5:]} TRIGGERED"))
        elif k == "order_sent" and r == "SELL_CLOSE":
            m = BA.search(d["reason_text"]); c.update(out_bid=float(m[1]), out_ask=float(m[2]))
        elif k == "fill" and r == "EXIT_FILL":
            c.update(out_t=tm, out_px=d["fill_price"]); c["events"].append((tm, f"SOLD {d['fill_price']:.2f}"))
        elif k == "trade_closed":
            c.update(pnl=d["pnl"]); trades.append(c); cur.pop(b, None)
    return series, state, trades, failed, orphans


def features(c, S):
    """Entry-time context and after-the-fact path stats for one trade, all in signal-time ATR units, signed to the trade."""
    s, a, p0, t0 = c["sgn"], c["atr"], c["sig_px"], c["sig_t"]
    def px(t): return S[t]["p"] if t in S else None
    back = [px(t0 - k) for k in (5, 15)]
    c["pre5"] = round(s * (p0 - back[0]) / a, 2) if back[0] else None
    c["pre15"] = round(s * (p0 - back[1]) / a, 2) if back[1] else None
    c["vwap_side"] = round(s * (p0 - c["vwap"]) / a, 2)
    c["e50_side"] = round(s * (p0 - c["e50"]) / a, 2)
    c["e921"] = round(s * (c["e9"] - c["e21"]) / a, 2)
    e50_10 = S.get(t0 - 10, {}).get("e50")
    c["e50_slope"] = round(s * (c["e50"] - e50_10) / a, 2) if e50_10 else None
    c["atr_bp"] = round(a / p0 * 1e4, 2)
    c["stop"], c["target"] = p0 - s * a, p0 + 2 * s * a
    end = c.get("out_t", 16 * 60)
    path = [s * (S[t]["p"] - p0) / a for t in range(t0 + 1, end + 1) if t in S]
    c["mfe"] = round(max([0] + path), 2); c["mae"] = round(min([0] + path), 2)
    post = [s * (S[t]["p"] - p0) / a for t in range(end + 1, end + 31) if t in S]
    c["post_mfe"] = round(max(post), 2) if post else None
    c["post_mae"] = round(min(post), 2) if post else None
    c["post_target"] = bool(post) and max(post) >= 2
    if "out_t" in c:
        c["hold"] = c["out_t"] - c["in_t"]
        c["out_R"] = round(s * (S[c["out_t"]]["p"] - p0) / a, 2) if c["out_t"] in S else None


def label(c):
    if c.get("orphan"): return "LOST AT RESTART"
    if c.get("why") == "TARGET": return "WORKED"
    if c["post_target"]: return "RIGHT SIDE, STOPPED FIRST"
    if c["mfe"] >= 1: return "GAVE BACK A 1R+ GAIN"
    if c["mfe"] < 0.25 and (c["pre5"] or 0) >= 1: return "CHASED AN EXTENDED MOVE"
    if c["mfe"] < 0.25: return "WRONG SIDE FROM THE START"
    return "CHOPPED OUT"


def part1(series, state, trades, failed, orphans):
    allc = sorted(trades + orphans, key=lambda c: (c["in_t"], c["bot"]))
    for n, c in enumerate(allc, 1):
        c["n"] = n; features(c, series[c["tk"]]); c["label"] = label(c)
    # timeline.csv
    with open(OUT + "timeline.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "bot", "dir", "minute", "phase", "close", "vwap", "ema9", "ema21", "ema50", "atr", "move_R", "to_stop_R", "to_target_R", "bot_state", "event"])
        for c in allc:
            S, s, a, p0 = series[c["tk"]], c["sgn"], c["atr"], c["sig_px"]
            end = c.get("out_t", c["in_t"] + 30); ev = collections.defaultdict(list)
            for t, e in c["events"]: ev[t].append(e)
            for t in range(c["sig_t"] - 5, end + 16):
                if t not in S: continue
                x = S[t]; mv = s * (x["p"] - p0) / a
                ph = "before" if t < c["sig_t"] else "signal" if t == c["sig_t"] else "holding" if t <= end else "after"
                st_ = state[c["bot"]].get(t, ("", ""))
                w.writerow([c["n"], c["bot"], c["dir"], hm(t), ph, x["p"], x["vwap"], x["e9"], x["e21"], x["e50"], x["atr"], round(mv, 3),
                            round(mv + 1, 3), round(2 - mv, 3), f"{st_[0]}/{st_[1]}", "; ".join(ev[t])])
    # trades.md
    L = ["# Every call, minute by minute: 2026-10-09", "",
         "Prices are the underlying's 1-minute close as the bot saw it. `move` is the close minus the signal close, in signal-time ATR, signed so + is in the trade's favour.",
         "Stop is at move -1.00, target at +2.00 (bar-close rule). Rows run from 5 minutes before the signal to 15 minutes after the exit.", ""]
    cnt = collections.Counter(c["label"] for c in allc)
    usd = collections.defaultdict(float)
    for c in allc: usd[c["label"]] += c.get("pnl", 0)
    L += ["## Failure labels", "", "| label | trades | logged P&L |", "|---|---|---|"]
    for k, v in cnt.most_common(): L.append(f"| {k} | {v} | {usd[k]:+.0f} |")
    L += ["", "Rules, first match wins: LOST AT RESTART (filled, never closed in the log); WORKED (target); RIGHT SIDE, STOPPED FIRST (stopped, then price reached the 2 ATR target within 30 min after the exit);",
          "GAVE BACK A 1R+ GAIN (was +1 ATR or better, then stopped); CHASED AN EXTENDED MOVE (never +0.25 ATR, and the 5 min before the signal already ran 1 ATR or more in the trade's direction);",
          "WRONG SIDE FROM THE START (never +0.25 ATR); CHOPPED OUT (the rest).", ""]
    for c in allc:
        S, s, a, p0 = series[c["tk"]], c["sgn"], c["atr"], c["sig_px"]
        pnl = f"{c['pnl']:+.0f}" if "pnl" in c else "not closed"
        L += [f"## #{c['n']} {c['bot']} {c['dir']} {c.get('contract','')}: {pnl}, {c['label']}", "",
              f"Signal {hm(c['sig_t'])} at {p0:.2f}, ATR {a:.3f} ({c['atr_bp']} bp). Stop {c['stop']:.2f}, target {c['target']:.2f}. "
              f"Before signal: {c['pre5']} ATR in 5 min, {c['pre15']} in 15 min. Price vs VWAP {c['vwap_side']:+} ATR, vs EMA50 {c['e50_side']:+}, EMA9-21 gap {c['e921']:+}, EMA50 slope (10 min) {c['e50_slope']}. "
              f"Best {c['mfe']:+}, worst {c['mae']:+}. 30 min after exit: best {c['post_mfe']}, worst {c['post_mae']}.", "",
              "| time | close | move | vwap | ema9 | ema21 | ema50 | atr | bot | event |", "|---|---|---|---|---|---|---|---|---|---|"]
        end = c.get("out_t", c["in_t"] + 30); ev = collections.defaultdict(list)
        for t, e in c["events"]: ev[t].append(e)
        for t in range(c["sig_t"] - 5, end + 16):
            if t not in S: continue
            x = S[t]; mv = s * (x["p"] - p0) / a
            mark = "**" if c["sig_t"] <= t <= end else ""
            st_ = state[c["bot"]].get(t, ("", ""))[1]
            L.append(f"| {mark}{hm(t)}{mark} | {x['p']:.2f} | {mv:+.2f} | {x['vwap']:.2f} | {x['e9']:.2f} | {x['e21']:.2f} | {x['e50']:.2f} | {x['atr']:.3f} | {st_} | {'; '.join(ev[t])} |")
        L.append("")
    L += ["## Entries that never filled", ""] + [f"- {hm(f['sig_t'])} {f['bot']} {f.get('dir','')} {f.get('contract','')} at {f['sig_px']:.2f}" for f in failed]
    open(OUT + "trades.md", "w").write("\n".join(L) + "\n")
    # features.csv
    cols = ["n", "bot", "tk", "trig", "dir", "label", "sig_t", "in_t", "out_t", "why", "pnl", "hold", "atr", "atr_bp", "pre5", "pre15", "vwap_side", "e50_side", "e921", "e50_slope",
            "mfe", "mae", "out_R", "post_mfe", "post_mae", "post_target", "retries"]
    with open(OUT + "features.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for c in allc: w.writerow([hm(c[k]) if k in ("sig_t", "in_t", "out_t") and c.get(k) is not None else c.get(k) for k in cols])
    P(f"PART 1: {len(trades)} closed + {len(orphans)} lost at restart + {len(failed)} not filled; logged P&L {sum(c['pnl'] for c in trades):+.0f}")
    for k, v in cnt.most_common(): P(f"  {k:28s} {v:3d}  {usd[k]:+7.0f}")
    return allc


# ======================= Part 2/3: historical simulator with exit variants =======================
VARIANTS = {
    "base 1/2 (live)":           dict(stop=1, tgt=2),
    "stop 1 / target 1":         dict(stop=1, tgt=1),
    "stop 1 / target 3":         dict(stop=1, tgt=3),
    "stop 1.5 / target 3":       dict(stop=1.5, tgt=3),
    "stop 2 / target 2":         dict(stop=2, tgt=2),
    "stop 2 / target 4":         dict(stop=2, tgt=4),
    "breakeven after +1R":       dict(stop=1, tgt=2, be=1),
    "trail 1R after +1R":        dict(stop=1, tgt=2, trail=1, trail_on=1),
    "no target, trail 1R":       dict(stop=1, tgt=None, trail=1, trail_on=1),
    "time stop 10 min":          dict(stop=1, tgt=2, tmax=10),
    "time stop 20 min":          dict(stop=1, tgt=2, tmax=20),
    "ATR floor 4bp":             dict(stop=1, tgt=2, floor_bp=4),
    "ATR floor 4bp, stop 1.5/3": dict(stop=1.5, tgt=3, floor_bp=4),
    "side = raw cross":          dict(stop=1, tgt=2, side="cross"),
    "side = opposite of live":   dict(stop=1, tgt=2, side="fade"),
}


def exit_check(p, close, end, v):
    """Shared exit rule for history and today's replay. Returns (why or None). Mutates trailing state."""
    s = p["sg"]; R = s * (close - p["ent"]) / p["R"]
    p["peak"] = max(p["peak"], R)
    if v.get("be") and p["peak"] >= v["be"]: p["stopR"] = max(p["stopR"], 0.0)
    if v.get("trail") and p["peak"] >= v["trail_on"]: p["stopR"] = max(p["stopR"], p["peak"] - v["trail"])
    if end >= T(15, 55): return "TIME", R
    if R <= p["stopR"]: return "STOP", R
    if v.get("tgt") and R >= v["tgt"]: return "TARGET", R
    if v.get("tmax") and (p["held"] >= v["tmax"]): return "TIMESTOP", R
    return None, R


def open_pos(d, close, atr, v, et, k):
    R = max(atr, close * v["floor_bp"] / 1e4) if v.get("floor_bp") else atr
    return dict(k=k, dir=d, sg=1 if d == "CALL" else -1, ent=close, atr=atr, R=R, stopR=-v["stop"], peak=0.0, et=et, held=0)


def simulate(D, v):
    trades = []
    for t in A.TICKERS:
        for day, xs in D[t].items():
            pos = {}; free = {b: None for b in A.BOTS}
            for k, x in enumerate(xs):
                end = x["end"]
                for b in list(pos):
                    p = pos[b]
                    if k <= p["k"]: continue
                    p["held"] += 1
                    why, R = exit_check(p, x["c"], end.time(), v)
                    if why is None and k == len(xs) - 1: why = "EOD"
                    if why:
                        dS = p["sg"] * (x["c"] - p["ent"])
                        trades.append(dict(t=t, bot=b, day=day, dir=p["dir"], R=dS / p["atr"], why=why, et=p["et"], hold=(end - p["et"]).total_seconds() / 60,
                                           atr=p["atr"], S=p["ent"], dS=dS, f=p["f"]))
                        del pos[b]; free[b] = end + timedelta(minutes=2)
                if end.time() < T(9, 31) or end.time() > T(15, 30): continue
                chop = abs(x["e9"] - x["e21"]) < 0.15 * x["atr"]
                for b in A.BOTS:
                    if b in pos or (free[b] and end < free[b]): continue
                    sig = x["sig"].get(b)
                    if not sig or (b == "vwap" and chop): continue
                    if b == "range" and end.time() < T(9, 46): continue
                    trend = "CALL" if x["e9"] > x["e21"] else "PUT" if x["e9"] < x["e21"] else sig
                    d = sig if v.get("side") == "cross" else trend
                    if v.get("side") == "fade": d = "PUT" if trend == "CALL" else "CALL"
                    p = open_pos(d, x["c"], x["atr"], v, end, k)
                    sg = p["sg"]; j5 = xs[max(0, k - 5)]["c"]
                    p["f"] = dict(pre5=sg * (x["c"] - j5) / x["atr"], e921=sg * (x["e9"] - x["e21"]) / x["atr"], atr_bp=x["atr"] / x["c"] * 1e4,
                                  hour=end.hour + end.minute / 60)
                    pos[b] = p
    return trades


def dollars(trades, byday, bytk):
    for x in trades:
        kk = byday.get((x["t"], str(x["day"])), bytk[x["t"]])
        tm = A.tmin(x["et"]) if not isinstance(x["et"], str) else A.tmin(datetime.fromisoformat(x["et"]))
        prem = kk * x["S"] * math.sqrt(tm)
        gross = A.QTY * 100 * A.DELTA * x["dS"]
        theta = A.QTY * 100 * prem / (2 * tm) * x["hold"]
        fees = 2 * A.QTY * A.FEE_SIDE
        x["gross$"] = gross
        x["net$"] = gross - theta - A.QTY * 100 * LIVE_SPREAD[x["t"]] * prem - fees
        x["net2$"] = gross - theta - A.QTY * 100 * 0.02 * prem - fees


def boot_ci(tr, key="net$", n=1000, seed=7):
    import random
    byd = collections.defaultdict(list)
    for x in tr: byd[x["day"]].append(x[key])
    keys = list(byd); rng = random.Random(seed); ms = []
    for _ in range(n):
        smp = [byd[rng.choice(keys)] for _ in keys]
        ms.append(sum(sum(v) for v in smp) / max(1, sum(len(v) for v in smp)))
    ms.sort(); return ms[int(.025 * n)], ms[int(.975 * n)], sum(1 for m in ms if m > 0) / n


def row(name, tr, ndays, ci=False):
    if not tr: return dict(variant=name, n=0)
    r = dict(variant=name, n=len(tr), per_day=round(len(tr) / ndays, 1), win=round(100 * sum(x["R"] > 0 for x in tr) / len(tr), 1),
             grossR=round(st.mean(x["R"] for x in tr), 3), gross_usd=round(st.mean(x["gross$"] for x in tr), 1),
             net_usd=round(st.mean(x["net$"] for x in tr), 1), net2_usd=round(st.mean(x["net2$"] for x in tr), 1),
             usd_day=round(sum(x["net$"] for x in tr) / ndays, 0), hold=round(st.mean(x["hold"] for x in tr), 1))
    if ci:
        lo, hi, pp = boot_ci(tr); r.update(ci_lo=round(lo, 1), ci_hi=round(hi, 1), p_pos=round(pp, 2))
    return r


def fmt(r):
    if not r.get("n"): return f"{r['variant']:28s} no trades"
    s = (f"{r['variant']:28s} n={r['n']:5d} ({r['per_day']:4.1f}/day) win={r['win']:4.1f}% grossR={r['grossR']:+.3f} gross$={r['gross_usd']:+6.1f} "
         f"net$={r['net_usd']:+6.1f} (2%: {r['net2_usd']:+6.1f}) $/day={r['usd_day']:+6.0f} hold={r['hold']:4.1f}m")
    if "ci_lo" in r: s += f" CI[{r['ci_lo']:+.1f},{r['ci_hi']:+.1f}] P>0={r['p_pos']:.2f}"
    return s


def replay_today(allc, series, v):
    """Each of today's actual entries (closed + lost at restart) re-run with exit variant v on the logged closes. Overlap between a bot's trades ignored."""
    out = []
    for c in allc:
        S = series[c["tk"]]; d = c["dir"]
        if v.get("side") == "fade": d = "PUT" if d == "CALL" else "CALL"
        if v.get("side") == "cross": continue
        p = open_pos(d, c["sig_px"], c["atr"], v, None, 0)
        why = None
        for t in range(c["sig_t"] + 1, 16 * 60):
            if t not in S: continue
            p["held"] += 1
            why, R = exit_check(p, S[t]["p"], T(t // 60, t % 60), v)
            if why: break
        dS = p["sg"] * (S[t]["p"] - p["ent"])
        et = datetime(2026, 10, 9, c["sig_t"] // 60, c["sig_t"] % 60, tzinfo=A.ET)
        out.append(dict(t=c["tk"], bot=c["bot"], day="2026-10-09", R=dS / c["atr"], why=why or "EOD", et=et, hold=t - c["sig_t"], atr=c["atr"], S=c["sig_px"], dS=dS))
    return out


def feature_table(tr, title):
    P(f"\n{title}: win rate and mean net $ by entry-time bucket (n per bucket in brackets)")
    def buckets(key, edges):
        res = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            xs = [x for x in tr if lo <= x["f"][key] < hi]
            if xs: res.append(f"[{lo:g},{hi:g}) n={len(xs)} win={100*sum(x['R']>0 for x in xs)/len(xs):.0f}% R={st.mean(x['R'] for x in xs):+.3f} net$={st.mean(x['net$'] for x in xs):+.0f}")
        P(f"  {key}: " + " | ".join(res))
    buckets("pre5", [-99, -1, 0, 1, 2, 99])
    buckets("e921", [-99, 0, 0.15, 0.5, 1, 99])
    buckets("atr_bp", [0, 2, 3, 4, 6, 99])
    buckets("hour", [9.5, 10, 11, 12, 13, 14, 15, 16])


def main():
    os.makedirs(OUT, exist_ok=True)
    series, state, trades, failed, orphans = read_log()
    allc = part1(series, state, trades, failed, orphans)

    # ---- Part 2a: today's features, winners vs losers ----
    closed = [c for c in allc if "pnl" in c]
    P("\nPART 2a, today: mean entry-time features, target trades vs stop trades (n is small; descriptive only)")
    for key in ("pre5", "pre15", "vwap_side", "e50_side", "e921", "e50_slope", "atr_bp"):
        a = [c[key] for c in closed if c["why"] == "TARGET" and c[key] is not None]
        b = [c[key] for c in closed if c["why"] == "STOP" and c[key] is not None]
        P(f"  {key:10s} targets {st.mean(a):+.2f} (n={len(a)})   stops {st.mean(b):+.2f} (n={len(b)})")
    pt = [c for c in closed if c["why"] == "STOP"]
    P(f"  stops that reached the 2 ATR target within 30 min after the exit: {sum(c['post_target'] for c in pt)} of {len(pt)}")
    P(f"  stops whose exit filled more than 0.25 ATR past the stop line: {sum(1 for c in pt if c['out_R'] is not None and c['out_R'] < -1.25)} of {len(pt)}")

    # ---- history ----
    D = {t: A.prepare(A.load(t)) for t in A.TICKERS}
    days = sorted(set(D["SPY"]) & set(D["QQQ"]) & set(D["IWM"]))
    for t in A.TICKERS: D[t] = collections.OrderedDict((d, v) for d, v in D[t].items() if d in days)
    byday, bytk = A.premium_model()
    train, val, hold = set(days[:50]), set(days[50:70]), set(days[70:])
    P(f"\nHISTORY {days[0]}..{days[-1]}, {len(days)} days: train {len(train)}, validation {len(val)}, holdout {len(hold)} ({min(hold)}..{max(hold)})")
    P("net$ = per trade, 10 contracts, today's quoted spread per ticker; (2%) = pessimistic 2% spread. CI = day-cluster bootstrap 95% on net$, holdout only.")

    base = simulate(D, VARIANTS["base 1/2 (live)"]); dollars(base, byday, bytk)
    feature_table([x for x in base if x["day"] in train | val], "PART 2b, history (train+validation, live rules)")

    rows = []
    P("\nPART 3a, exit variants on 90 days of history (same entry rules; counts move only because a bot is busy longer or shorter)")
    for name, v in VARIANTS.items():
        tr = base if name.startswith("base") else simulate(D, v)
        if not name.startswith("base"): dollars(tr, byday, bytk)
        for split, ds in (("dev", train | val), ("holdout", hold)):
            r = row(name, [x for x in tr if x["day"] in ds], len(ds), ci=(split == "holdout")); r["split"] = split; rows.append(r)
    for split in ("dev", "holdout"):
        P(f"\n  -- {split} --")
        for r in rows:
            if r["split"] == split: P("  " + fmt(r))

    P("\nPART 3b, the same variants on today's actual entries (each entry replayed alone on the logged closes, so overlap with the bot's next trade is ignored)")
    P("  logged P&L of these entries: " + f"{sum(c.get('pnl', 0) for c in allc):+.0f} (lost-at-restart positions count as 0 here)")
    for name, v in VARIANTS.items():
        tr = replay_today(allc, series, v)
        if not tr: P(f"  {name:28s} not replayable from the log"); continue
        dollars(tr, {}, {"SPY": 0.00009, "QQQ": 0.00014, "IWM": 0.00014})   # live k fitted in analysis-2026-10-09
        r = row(name, tr, 1); r["split"] = "today"; rows.append(r)
        P("  " + fmt(r) + f"  total net$={sum(x['net$'] for x in tr):+.0f}")

    with open(OUT + "variants.csv", "w", newline="") as f:
        keys = ["split", "variant", "n", "per_day", "win", "grossR", "gross_usd", "net_usd", "net2_usd", "usd_day", "hold", "ci_lo", "ci_hi", "p_pos"]
        w = csv.DictWriter(f, keys, extrasaction="ignore"); w.writeheader(); [w.writerow(r) for r in rows]
    open(OUT + "output.txt", "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
