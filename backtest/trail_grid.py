"""Exit-shape grid: the live Scalp City V2 trail against Nick Fischer's give-back-half trail.

Research script, paper only, no network. Entries are held fixed (the live triggers from filters.py) so the
only thing that varies is the exit. Everything is measured on the UNDERLYING in ATR units at entry
(1 R = 1 ATR at entry), the same convention as filters.py and stops_targets.py.

Exit shapes compared:
  stop_target     1 ATR stop, 2 ATR target (Scalp City V1)
  live_v2         1 ATR stop, no target; once a close is arm x ATR(entry) in favour, trail trail_atr x the
                  CURRENT ATR behind the best close, ratcheting, never looser than the initial stop
  giveback        stop_atr stop, no target; once a close is arm x ATR(entry) in favour, the exit level sits
                  give of the way back from the best close to the entry (give=0.5 is Fischer's "gives back
                  half"), ratcheting, never looser than the initial stop

Fischer's stated rules (source: research/nick-fisher/rules.md, S07) are arm 4.0, give 0.5, stop 10.0.
His 10 ATR stop is a wipeout marker, not a risk control, so the grid also pairs his trail shape with our
1 ATR stop.

Trail levels are evaluated on bar closes, matching the live engine. The hard stop is checked intrabar on
the bar high/low and takes priority inside a bar, which flatters tight stops (real stops slip).

CAVEAT: this is an underlying-price model. It carries no option convexity, no theta and no spread beyond the
flat COST_R sensitivity. Give-back-half holds trades materially longer than the live trail, and the extra
theta that implies is NOT modelled here. Hold time is reported so the drag can be judged separately. Treat
the ranking as directional, not as a P&L forecast.
"""
import collections
import json
import math
import os
import statistics as st
import sys
from datetime import date, datetime, timedelta, time as T

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filters as F

COST_R = 0.2          # legacy pooled constant, kept so older rows stay comparable
# Per-ticker round-trip cost in ATR units, MEASURED from Webull quotes and the option-bar delta fit
# (reports/premium-fit-2026-11-17/report.md). Same two-cent spread on QQQ and IWM, but IWM's
# 1-minute ATR is a third of QQQ's, so the same spread is 3-4x the drag in R terms.
COST_BY_TICKER = {"QQQ": 0.094, "SPY": 0.079, "IWM": 0.313}
FILT = dict(buffer=0.2, trend=True, chop_all=True)


def load_range(t, suffix):
    """filters.load against an explicit date-ranged file from fetch_stock_range.py."""
    import json as _json
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _Z
    ET = _Z("America/New_York")
    out = []
    for b in _json.load(open(f"backtest/data/{t}_1m_{suffix}.json")):
        s_ = _dt.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET)
        if T(9, 30) <= s_.time() < T(16, 0):
            out.append((s_, b["o"], b["h"], b["l"], b["c"], b["v"]))
    return out


def run_exit(t, rows, cfg, ex):
    """filters.run with a pluggable exit. `ex` names the exit shape and its parameters."""
    kind = ex["kind"]
    sa = ex.get("stop", 1.0)
    trades = []
    byday = collections.defaultdict(list)
    for r in rows:
        byday[r["t"].date()].append(r)
    for day, xs in byday.items():
        for bot in ("vwap", "ema50", "range"):
            k = 0
            free_at = None
            block = None
            while k < len(xs) - 1:
                x = xs[k]
                end = x["t"] + timedelta(minutes=1)
                if end.time() > F.LAST_ENTRY or (bot == "range" and end.time() < T(9, 45)) or (free_at and end < free_at):
                    k += 1
                    continue
                sig = F.signal(xs, k, bot, cfg)
                if not sig:
                    k += 1
                    continue
                if cfg.get("noreentry") and block == sig:
                    k += 1
                    continue
                if cfg.get("noreentry") and block and block != sig:
                    block = None

                ent = x["c"]
                atr0 = x["atr"]
                call = sig == "CALL"
                stop = ent - sa * atr0 if call else ent + sa * atr0
                tgt = None
                if kind == "stop_target":
                    ta = ex.get("tgt", 2.0)
                    tgt = ent + ta * atr0 if call else ent - ta * atr0

                best = ent              # best CLOSE seen so far, in the trade's favour
                level = stop            # current exit level; ratchets in the trade's favour only
                armed = False
                j = k + 1
                why, R, exit_end, held = "TIME", 0.0, None, 0
                while j < len(xs):
                    y = xs[j]
                    h, l, c = F.bars_hl[(t, y["i"])]
                    yend = y["t"] + timedelta(minutes=1)
                    held = j - k

                    # hard level first, intrabar, conservative
                    hit = l <= level if call else h >= level
                    if hit:
                        px = level
                        why = "STOP" if level == stop else "TRAIL"
                        R = ((px - ent) if call else (ent - px)) / atr0
                        exit_end = yend
                        break
                    if tgt is not None:
                        hit_t = h >= tgt if call else l <= tgt
                        if hit_t:
                            why, R, exit_end = "TARGET", ex.get("tgt", 2.0), yend
                            break

                    # trail update on the bar close
                    if kind in ("live_v2", "giveback"):
                        if (c > best) if call else (c < best):
                            best = c
                        fav = (best - ent) if call else (ent - best)
                        if not armed and fav >= ex["arm"] * atr0:
                            armed = True
                        if armed:
                            if kind == "live_v2":
                                cand = best - ex["trail_atr"] * y["atr"] if call else best + ex["trail_atr"] * y["atr"]
                            else:
                                cand = best - ex["give"] * fav if call else best + ex["give"] * fav
                            cand = max(cand, stop) if call else min(cand, stop)
                            level = max(level, cand) if call else min(level, cand)

                    if yend.time() >= F.FLAT or j == len(xs) - 1:
                        R = ((c - ent) if call else (ent - c)) / atr0
                        exit_end = yend
                        break
                    j += 1

                trades.append(dict(t=t, bot=bot, day=day, R=R, why=why, dir=sig, held=held))
                if why == "STOP":
                    block = sig
                free_at = exit_end + timedelta(minutes=F.COOL)
                while k < len(xs) and xs[k]["t"] + timedelta(minutes=1) < free_at:
                    k += 1
    return trades


def stats(tr, blocks):
    R = [x["R"] for x in tr]
    Rc = [x["R"] - COST_BY_TICKER[x["t"]] for x in tr]
    n = len(R)
    if n < 2:
        return None
    m = st.mean(R)
    se = st.stdev(R) / math.sqrt(n)
    wins = [r for r in R if r > 0]
    losses = [r for r in R if r <= 0]
    pos = sum(1 for b in blocks if any(x["day"] in b for x in tr)
              and st.mean([x["R"] for x in tr if x["day"] in b]) > 0)
    held = [x["held"] for x in tr]
    mc = st.mean(Rc)
    sec = st.stdev(Rc) / math.sqrt(n)
    return dict(
        trades=n, win=100 * len(wins) / n, avgR=m, totR=sum(R), t=m / se, after=m - COST_R,
        afterTkr=mc, totR_afterTkr=sum(Rc), t_afterTkr=mc / sec,
        win_afterTkr=100 * sum(1 for r in Rc if r > 0) / n,
        avgwin=st.mean(wins) if wins else 0.0, avgloss=st.mean(losses) if losses else 0.0,
        maxwin=max(R), maxloss=min(R), blocks=pos,
        medheld=st.median(held), meanheld=st.mean(held),
    )


GRID = [
    ("stop_target 1.0/2.0 (V1)",          dict(kind="stop_target", stop=1.0, tgt=2.0)),
    ("live_v2 stop1.0 arm0.5 trail1.5",   dict(kind="live_v2", stop=1.0, arm=0.5, trail_atr=1.5)),
]
for stop in (1.0, 2.0, 10.0):
    for arm in (0.5, 1.0, 2.0, 4.0):
        for give in (0.25, 0.5, 0.75):
            GRID.append((f"giveback stop{stop:g} arm{arm:g} give{give:g}",
                         dict(kind="giveback", stop=stop, arm=arm, give=give)))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--suffix", default=None, help="date range of the data files, e.g. 2025-11-17_2026-11-14")
    ap.add_argument("--last-entry", default="10:59", help="last entry time ET; live is 10:59, legacy harness 15:30")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    hh, mm = (int(x) for x in a.last_entry.split(":"))
    F.LAST_ENTRY = T(hh, mm)

    out_dir = os.path.join("reports", f"trail-giveback-{date.today():%Y-%m-%d}{a.tag}")
    os.makedirs(out_dir, exist_ok=True)

    allrows = {}
    for t in F.TICKERS:
        bars = load_range(t, a.suffix) if a.suffix else F.load(t)
        for i, (s, o, h, l, c, v) in enumerate(bars):
            F.bars_hl[(t, i)] = (h, l, c)
        allrows[t] = F.prepare(bars)
    days = sorted({r["t"].date() for r in allrows["SPY"]})
    months = sorted({(d.year, d.month) for d in days})
    blocks = [{d for d in days if (d.year, d.month) == m} for m in months]
    cut6 = days[-126] if len(days) > 126 else days[0]      # ~6 months of trading days
    print(f"days {days[0]}..{days[-1]} ({len(days)}), {len(months)} months, "
          f"last-6mo from {cut6}, entries to {F.LAST_ENTRY}\n", flush=True)

    rows = []
    for label, base in (("baseline entries", {}), ("filtered entries (buffer 0.2 + trend + chop all)", FILT)):
        for name, ex in GRID:
            tr = [x for t in F.TICKERS for x in run_exit(t, allrows[t], base, ex)]
            s = stats(tr, blocks)
            if not s:
                continue
            for tkr in F.TICKERS:
                b = stats([x for x in tr if x["t"] == tkr], blocks)
                if b:
                    s_tkr = s.setdefault("per_ticker", {}) if False else None
            s6 = stats([x for x in tr if x["day"] >= cut6], blocks)
            s.update(entries=label, exit=name, **{k: v for k, v in ex.items() if k != "kind"}, kind=ex["kind"])
            s["months_pos"] = f"{s['blocks']}/{len(blocks)}"
            if s6:
                s["avgR_6mo"], s["trades_6mo"], s["t_6mo"] = s6["avgR"], s6["trades"], s6["t"]
            by_bot = {}
            for bot in ("vwap", "ema50", "range"):
                b = stats([x for x in tr if x["bot"] == bot], blocks)
                if b:
                    by_bot[bot] = dict(trades=b["trades"], avgR=round(b["avgR"], 4), win=round(b["win"], 1))
            s["by_bot"] = by_bot
            s["by_ticker"] = {}
            for tkr in F.TICKERS:
                b = stats([x for x in tr if x["t"] == tkr], blocks)
                if b:
                    s["by_ticker"][tkr] = dict(trades=b["trades"], avgR=round(b["avgR"], 4),
                                               afterTkr=round(b["afterTkr"], 4),
                                               t_afterTkr=round(b["t_afterTkr"], 3))
            noi = stats([x for x in tr if x["t"] != "IWM"], blocks)
            if noi:
                s["ex_IWM"] = dict(trades=noi["trades"], afterTkr=round(noi["afterTkr"], 4),
                                   t_afterTkr=round(noi["t_afterTkr"], 3))
            qo = stats([x for x in tr if x["t"] == "QQQ"], blocks)
            if qo:
                s["qqq_only"] = dict(trades=qo["trades"], avgR=round(qo["avgR"], 4),
                                     afterTkr=round(qo["afterTkr"], 4),
                                     t_afterTkr=round(qo["t_afterTkr"], 3),
                                     months_pos=f"{qo['blocks']}/{len(blocks)}")
            rows.append(s)
            print(f"{label[:9]:9s} {name:36s} {s['trades']:5d}tr win{s['win']:5.1f}% avgR{s['avgR']:+.3f} "
                  f"t{s['t']:+5.2f} flat{s['after']:+.3f} tkr{s['afterTkr']:+.3f} "
                  f"t{s['t_afterTkr']:+5.2f} exIWM{s.get('ex_IWM',{}).get('afterTkr',float('nan')):+.3f} "
                  f"QQQ{s.get('qqq_only',{}).get('afterTkr',float('nan')):+.3f} "
                  f"t{s.get('qqq_only',{}).get('t_afterTkr',float('nan')):+5.2f} "
                  f"mo{s['months_pos']:>6s} held~{s['medheld']:.0f}m", flush=True)

    with open(os.path.join(out_dir, "results.json"), "w") as f:
        json.dump(dict(
            generated=datetime.now().isoformat(timespec="seconds"),
            days=[str(days[0]), str(days[-1])], n_days=len(days), n_months=len(months),
            six_month_cut=str(cut6), last_entry=str(F.LAST_ENTRY), tickers=list(F.TICKERS),
            cost_R=COST_R, cost_by_ticker=COST_BY_TICKER, rows=rows), f, indent=1, default=str)

    with open(os.path.join(out_dir, "results.csv"), "w") as f:
        cols = ["entries", "exit", "kind", "stop", "arm", "give", "trail_atr", "tgt",
                "trades", "win", "avgR", "after", "afterTkr", "t_afterTkr", "win_afterTkr",
                "totR", "totR_afterTkr", "t", "blocks", "months_pos",
                "trades_6mo", "avgR_6mo", "t_6mo",
                "avgwin", "avgloss", "maxwin", "maxloss", "medheld", "meanheld"]
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join("" if r.get(c) is None else
                             (f"{r[c]:.4f}" if isinstance(r.get(c), float) else str(r.get(c, "")))
                             for c in cols) + "\n")
    print(f"\nwrote {out_dir}/results.json and results.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
