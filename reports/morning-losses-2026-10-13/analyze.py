"""Opening trades vs the rest of the day, from the live event logs. Run from repo root."""
import json, collections
DAYS = ["2026-10-09", "2026-10-12", "2026-10-13"]
for day in DAYS:
    ev = [json.loads(l) for l in open(f"logs/{day}-live.jsonl")]
    entry, buckets, rows = {}, collections.defaultdict(list), []
    exit_px = {}
    for e in ev:
        if e["kind"] == "fill" and e["reason_code"] == "ENTRY_FILL":
            entry[e["bot"]] = e
        if e["kind"] == "trade_closed" and e["bot"] in entry:
            en = entry.pop(e["bot"])
            t = en["time"][11:16]
            b = "09:30-09:45" if t < "09:45" else "09:45-10:30" if t < "10:30" else "10:30+"
            atr = (en.get("inputs") or {}).get("atr")
            buckets[b].append(e["pnl"])
            if b == "09:30-09:45":
                rows.append(f"  {t} {e['bot']:10} entry {en['fill_price']} atr {atr} pnl {e['pnl']:+.0f} held {e['time'][11:16]}")
    print(day)
    for b in ("09:30-09:45", "09:45-10:30", "10:30+"):
        p = buckets[b]
        if p:
            print(f"  {b}: {len(p)} trades, {sum(x > 0 for x in p)} wins, net {sum(p):+.0f}, avg {sum(p)/len(p):+.0f}")
    print("\n".join(rows))
