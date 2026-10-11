"""Line-by-line review of one day's live paper trades from the event log. Read-only. Paper only.
Usage: .venv/bin/python scripts/trade_review.py [YYYY-MM-DD]   -> reports/<day>-trade-review.md and .csv
Each trade gets issue tags computed from the log alone (no broker calls):
  REENTRY    same bot entered the same direction within 5 min of its own stop
  FLIP       same bot entered the opposite direction within 10 min of its previous exit
  HEDGED     another bot already held the opposite direction on the same ticker at entry
  DUP        another bot entered the same ticker and direction in the same minute (one idea counted twice)
  NO_FOLLOW  the underlying never moved 0.25 ATR in the trade's favor
  QUICK_STOP stopped out within 3 minutes
  OFFMKT     entry or exit fill priced outside the quote's bid/ask (sandbox fill, not a real market price)
  EXIT_RETRY the exit order failed to fill at least once first
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime

DAY = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
LOG = f"logs/{DAY}-live.jsonl"
BA = re.compile(r"bid/ask ([\d.]+)/([\d.]+)")


def t(s): return datetime.fromisoformat(s)
def hm(s): return s[11:19]


def main():
    ev = [json.loads(l) for l in open(LOG)]
    cur, trades, failed, held = {}, [], [], {}
    skips = defaultdict(int)
    for d in ev:
        b, k, r = d["bot"], d["kind"], d["reason_code"]
        c = cur.get(b)
        if k == "state_change" and r == "SIGNAL":
            cur[b] = c = dict(bot=b, tk=d["ticker"], sig_t=d["time"], sig_px=d["inputs"].get("price"), exit_retries=0, mfe=0.0, mae=0.0, on=False)
        elif k == "state_change" and r == "CHOP_SQUEEZE": skips["squeeze"] += 1
        elif k == "order_sent" and r == "BUY_OPEN" and c:
            m = BA.search(d["reason_text"]); sgn = 1 if d["contract"][len(d["ticker"]) + 6] == "C" else -1
            c.update(contract=d["contract"], dir="CALL" if sgn == 1 else "PUT", sgn=sgn, p0=d["inputs"]["price"], atr=d["inputs"].get("atr"),
                     in_bid=float(m.group(1)), in_ask=float(m.group(2)), ord_t=d["time"], seq=d["seq"])
        elif k == "state_change" and r == "ORDER_FAILED" and c and "contract" in c:
            failed.append(dict(bot=b, t=d["time"], what="ENTRY", contract=c["contract"], why=d["reason_text"])); cur.pop(b, None)
        elif k == "fill" and r == "ENTRY_FILL" and c:
            c.update(in_t=d["time"], in_px=d["fill_price"], in_src=d.get("fill_source"), on=True)
            held[b] = (c["tk"], c["dir"])
        elif k == "tick" and c and c.get("on") and d["inputs"].get("price"):
            mv = (d["inputs"]["price"] - c["p0"]) * c["sgn"] / c["atr"]; c["mfe"] = max(c["mfe"], mv); c["mae"] = min(c["mae"], mv)
        elif k == "state_change" and r.startswith("EXIT_") and c and c.get("on"):
            if r == "EXIT_RETRY": c["exit_retries"] += 1
            else: c["why"] = r.replace("EXIT_", "")
        elif k == "order_sent" and r == "SELL_CLOSE" and c and c.get("on"):
            m = BA.search(d["reason_text"]); c.update(out_bid=float(m.group(1)), out_ask=float(m.group(2)), p1=d["inputs"]["price"])
        elif k == "fill" and r == "EXIT_FILL" and c and c.get("on"):
            c.update(out_t=d["time"], out_px=d["fill_price"], out_src=d.get("fill_source"))
        elif k == "trade_closed" and c and c.get("on"):
            c.update(pnl=d["pnl"], pnl_day=d["pnl_day"]); trades.append(c); held.pop(b, None); cur.pop(b, None)
    open_now = [c for c in cur.values() if c.get("on")]

    # tags
    last_exit = {}
    for i, c in enumerate(trades, 1):
        c["n"] = i; tags = []
        prev = last_exit.get(c["bot"])
        if prev:
            gap = (t(c["in_t"]) - t(prev["out_t"])).total_seconds() / 60
            if prev["why"] == "STOP" and prev["dir"] == c["dir"] and gap <= 5: tags.append("REENTRY")
            if prev["dir"] != c["dir"] and gap <= 10: tags.append("FLIP")
        for o in trades + open_now:
            if o is c or o["bot"] == c["bot"] or o["tk"] != c["tk"] or "in_t" not in o: continue
            o_out = o.get("out_t", "9999")
            if o["in_t"] <= c["in_t"] < o_out and o["dir"] != c["dir"]: tags.append("HEDGED"); break
        if any(o is not c and o["tk"] == c["tk"] and o["dir"] == c["dir"] and o["in_t"][:16] == c["in_t"][:16] for o in trades + open_now if "in_t" in o): tags.append("DUP")
        if c["mfe"] < 0.25: tags.append("NO_FOLLOW")
        hold = (t(c["out_t"]) - t(c["in_t"])).total_seconds() / 60; c["hold"] = hold
        if c["why"] == "STOP" and hold <= 3: tags.append("QUICK_STOP")
        off = lambda px, bid, ask: not (bid - 0.011 <= px <= ask + 0.011)
        if off(c["in_px"], c["in_bid"], c["in_ask"]) or off(c["out_px"], c["out_bid"], c["out_ask"]): tags.append("OFFMKT")
        if c["exit_retries"]: tags.append("EXIT_RETRY")
        c["tags"] = tags; last_exit[c["bot"]] = c
        # cost vs quote mid, in dollars for the whole order (10 contracts x 100)
        qty = 1000
        c["in_cost"] = round((c["in_px"] - (c["in_bid"] + c["in_ask"]) / 2) * qty)
        c["out_cost"] = round(((c["out_bid"] + c["out_ask"]) / 2 - c["out_px"]) * qty)

    cols = ["n", "bot", "dir", "contract", "sig_t", "sig_px", "in_t", "in_bid", "in_ask", "in_px", "out_t", "why", "out_bid", "out_ask", "out_px",
            "pnl", "hold", "atr", "mfe", "mae", "in_cost", "out_cost", "tags"]
    os.makedirs("reports", exist_ok=True)
    with open(f"reports/{DAY}-trade-review.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for c in trades: w.writerow([";".join(c[k]) if k == "tags" else (round(c[k], 3) if isinstance(c[k], float) else c[k]) for k in cols])

    tag_n = defaultdict(lambda: [0, 0.0])
    for c in trades:
        for g in c["tags"]: tag_n[g][0] += 1; tag_n[g][1] += c["pnl"]
    tot = sum(c["pnl"] for c in trades)
    L = [f"# Trade review {DAY}", "", f"{len(trades)} closed trades, net **{tot:+.0f}**; {len(open_now)} still open; {len(failed)} entries failed to fill; {skips['squeeze']} squeeze skips.",
         "Times are ET. Prices are option premiums. `cost` columns = dollars paid versus quote mid (negative = filled better than mid).", "",
         "## Issue tags", "", "| tag | trades | net P&L |", "|---|---|---|"]
    for g, (n, p) in sorted(tag_n.items(), key=lambda x: x[1][1]):
        L.append(f"| {g} | {n} | {p:+.0f} |")
    L += ["", "## Every trade", "", "| # | bot | dir | signal (und) | in | in fill (bid/ask) | out | why | out fill (bid/ask) | P&L | hold | MFE/MAE ATR | cost in/out | tags |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in trades:
        L.append(f"| {c['n']} | {c['bot']} | {c['dir']} | {hm(c['sig_t'])[:5]} @ {c['sig_px']:.2f} | {hm(c['in_t'])[:5]} | {c['in_px']:.2f} ({c['in_bid']}/{c['in_ask']}) | {hm(c['out_t'])[:5]} | {c['why']} | "
                 f"{c['out_px']:.2f} ({c['out_bid']}/{c['out_ask']}) | {c['pnl']:+.0f} | {c['hold']:.0f}m | {c['mfe']:+.2f}/{c['mae']:+.2f} | {c['in_cost']:+d}/{c['out_cost']:+d} | {' '.join(c['tags'])} |")
    if open_now:
        L += ["", "## Still open", ""] + [f"- {c['bot']} {c['dir']} {c['contract']} in {hm(c['in_t'])[:5]} @ {c['in_px']:.2f}" for c in open_now]
    if failed:
        L += ["", "## Entries that did not fill", ""] + [f"- {hm(f['t'])[:5]} {f['bot']} {f['contract']}: {f['why']}" for f in failed]
    open(f"reports/{DAY}-trade-review.md", "w").write("\n".join(L) + "\n")
    print(f"{len(trades)} trades, net {tot:+.0f}; wrote reports/{DAY}-trade-review.md and .csv")
    for g, (n, p) in sorted(tag_n.items(), key=lambda x: x[1][1]): print(f"  {g:11s} {n:3d} trades  {p:+7.0f}")


if __name__ == "__main__":
    main()
