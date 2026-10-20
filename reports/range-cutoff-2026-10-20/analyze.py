"""Range-bot P&L by time of day across the Webull paper (live-mode) days.

Reads every logs/*-live.jsonl event log, rebuilds closed trades with scalpcity.history.build_trades,
buckets them by entry time (15 minutes, MDT), and reports for each candidate cutoff what a
"no new entries after this time" rule would have kept and cut, in total and per day.
Outputs: trades.csv, buckets.csv, cutoffs.csv, cutoffs_by_day.csv, summary.txt (this folder).
"""
import csv
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, time
from zoneinfo import ZoneInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from scalpcity.history import build_trades, read_day  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(ROOT, "logs")
MT = ZoneInfo("America/Denver")
ONLY_RANGE = "--all-bots" not in sys.argv


def is_range(bot: str) -> bool:
    return "range" in (bot or "").lower()


days = sorted({m.group(1) for n in os.listdir(LOGS) if (m := re.match(r"^(\d{4}-\d{2}-\d{2})-live\.jsonl$", n))})
rows, all_bots = [], set()
for day in days:
    for t in build_trades(read_day(LOGS, day, "live") or []):
        all_bots.add(t["bot"])
        if not isinstance(t.get("pnl"), (int, float)) or not t.get("entry_time"):
            continue
        if ONLY_RANGE and not is_range(t["bot"]):
            continue
        et = datetime.fromisoformat(t["entry_time"]).astimezone(MT)
        mins = et.hour * 60 + et.minute
        b = (mins // 15) * 15
        rows.append({"day": day, "bot": t["bot"], "entry_mt": et.strftime("%H:%M"), "bucket_mt": f"{b // 60:02d}:{b % 60:02d}",
                     "exit_code": t.get("exit_code"), "pnl": round(t["pnl"], 2)})

with open(os.path.join(OUT, "trades.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["day"])
    w.writeheader(); w.writerows(rows)


def stats(xs):
    n = len(xs); p = sum(x["pnl"] for x in xs); wins = sum(x["pnl"] > 0 for x in xs)
    return n, round(p, 2), (round(100 * wins / n, 1) if n else None)


buckets = defaultdict(list)
for r in rows:
    buckets[r["bucket_mt"]].append(r)
with open(os.path.join(OUT, "buckets.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["bucket_mt", "trades", "pnl", "win_pct", "days_positive", "days_negative"] + days)
    for b in sorted(buckets):
        per = {d: round(sum(x["pnl"] for x in buckets[b] if x["day"] == d), 2) for d in days}
        traded = [d for d in days if any(x["day"] == d for x in buckets[b])]
        w.writerow([b, *stats(buckets[b]), sum(per[d] > 0 for d in traded), sum(per[d] < 0 for d in traded)] + [per[d] for d in days])

cutoffs = [time(h, m) for h in range(7, 14) for m in (0, 15, 30, 45) if time(7, 45) <= time(h, m) <= time(14, 0)]
with open(os.path.join(OUT, "cutoffs.csv"), "w", newline="") as f, open(os.path.join(OUT, "cutoffs_by_day.csv"), "w", newline="") as g:
    w = csv.writer(f); w.writerow(["cutoff_mt", "kept_trades", "kept_pnl", "kept_win_pct", "cut_trades", "cut_pnl", "cut_win_pct", "days_cut_pnl_negative", "days_cut_pnl_positive"])
    v = csv.writer(g); v.writerow(["cutoff_mt"] + [f"{d}_cut_pnl" for d in days])
    for c in cutoffs:
        cs = c.strftime("%H:%M")
        kept = [r for r in rows if r["entry_mt"] < cs]; cut = [r for r in rows if r["entry_mt"] >= cs]
        per = {d: round(sum(x["pnl"] for x in cut if x["day"] == d), 2) for d in days}
        w.writerow([cs, *stats(kept), *stats(cut), sum(per[d] < 0 for d in days), sum(per[d] > 0 for d in days)])
        v.writerow([cs] + [per[d] for d in days])

with open(os.path.join(OUT, "summary.txt"), "w") as f:
    f.write(f"days: {days}\nall bots seen: {sorted(all_bots)}\nfilter: {'range bots only' if ONLY_RANGE else 'all bots'}\n")
    f.write(f"trades analysed: {len(rows)}  total pnl: {stats(rows)[1]}\n")
print(open(os.path.join(OUT, "summary.txt")).read())
