"""Five-day paper review (2026-10-09, 12, 13, 14, 15). Reads logs/*-live.jsonl and Webull bars in data/webull/<day>/.
One row per closed trade: signal, raw trigger direction vs traded side, exit reason, P&L, hold time,
underlying excursion while held (in ATR of the signal bar), stop overshoot, and what price did in the 30 min after exit.
Run from the repo root. Writes trades.csv and output.txt next to this file."""
import csv, glob, json, os
from collections import defaultdict
from datetime import datetime, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
DAYS = ["2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"]


def load_bars(day, ticker):
    rows = json.load(open(f"data/webull/{day}/stock-{ticker}.json"))
    out = []
    for b in rows:
        t = (datetime.fromisoformat(b["time"].replace(".000+0000", "+00:00")) - timedelta(hours=4)).strftime("%H:%M")
        out.append({"t": t, "o": float(b["open"]), "h": float(b["high"]), "l": float(b["low"]), "c": float(b["close"]), "v": float(b["volume"])})
    return out


trades, failed = [], defaultdict(lambda: defaultdict(int))
for day in DAYS:
    bars = {t: load_bars(day, t) for t in ("SPY", "QQQ", "IWM")}
    orb = {t: (max(b["h"] for b in bs if "09:30" <= b["t"] <= "09:44"), min(b["l"] for b in bs if "09:30" <= b["t"] <= "09:44")) for t, bs in bars.items()}
    cur = {}
    for line in open(f"logs/{day}-live.jsonl"):
        e = json.loads(line)
        bot, code, kind = e["bot"], e.get("reason_code"), e["kind"]
        if kind == "state_change" and code == "SIGNAL":
            cur[bot] = {"sig": e, "exit_reason": None, "retries": 0}
        elif kind == "state_change" and code == "ORDER_FAILED":
            failed[day][bot] += 1
            cur.pop(bot, None)
        elif kind == "state_change" and code == "EXIT_RETRY" and bot in cur:
            cur[bot]["retries"] += 1
        elif kind == "state_change" and code and code.startswith("EXIT_") and code != "EXIT_RETRY" and bot in cur:
            cur[bot]["exit_reason"] = cur[bot]["exit_reason"] or code[5:]
            cur[bot].setdefault("exit_sig_time", e["time"][11:16])
            cur[bot].setdefault("exit_sig_price", e["inputs"].get("price"))
        elif kind == "fill" and code == "ENTRY_FILL" and bot in cur:
            cur[bot]["entry"] = e
        elif kind == "fill" and code == "EXIT_FILL" and bot in cur:
            cur[bot]["exit"] = e
        elif kind == "trade_closed" and bot in cur:
            c = cur.pop(bot)
            s, inp = c["sig"], c["sig"]["inputs"]
            tk, strat = e["ticker"], bot.split("-")[1]
            price, atr = inp["price"], inp["atr"]
            side = "CALL" if s["reason_text"].startswith("CALL") else "PUT"
            sgn = 1 if side == "CALL" else -1
            if strat == "VWAP":
                raw = "CALL" if price > inp["vwap"] else "PUT"
            elif strat == "EMA50":
                raw = "CALL" if price > inp["ema50"] else "PUT"
            else:
                raw = "CALL" if price > orb[tk][0] else "PUT"
            trend = "CALL" if inp["ema9"] > inp["ema21"] else "PUT"
            et, xt = s["time"][11:16], e["time"][11:16]
            bs = bars[tk]
            idx = {b["t"]: i for i, b in enumerate(bs)}
            i0, i1 = idx.get(et), idx.get(xt, len(bs) - 1)
            held = bs[i0 + 1:i1 + 1] if i0 is not None else []
            mfe = max((sgn * ((b["h"] if sgn > 0 else b["l"]) - price) for b in held), default=0) / atr
            mae = max((-sgn * ((b["l"] if sgn > 0 else b["h"]) - price) for b in held), default=0) / atr
            after = bs[i1 + 1:i1 + 31]
            exit_und = c.get("exit_sig_price") or e["inputs"]["price"]
            post_fav = max((sgn * ((b["h"] if sgn > 0 else b["l"]) - price) for b in after), default=0) / atr
            hit_target_later = post_fav >= 2.0
            # stop overshoot: how far past 1 ATR against the entry the bar close was when the stop fired
            stop_dist = -sgn * (exit_und - price) / atr
            en, ex = c.get("entry", {}), c.get("exit", {})
            mins = (datetime.strptime(xt, "%H:%M") - datetime.strptime(et, "%H:%M")).seconds // 60
            vol20 = [b["v"] for b in bs[max(0, i0 - 20):i0]] if i0 else []
            trades.append({
                "day": day, "bot": bot, "strategy": strat, "ticker": tk, "entry_time": et, "exit_time": xt, "hold_min": mins,
                "side": side, "raw_cross": raw, "flipped": raw != side, "trend_ema9_21": trend,
                "exit_reason": c["exit_reason"] or "?", "pnl": e["pnl"], "atr": atr, "atr_pct": round(100 * atr / price, 4),
                "price": price, "dist_vwap_atr": round((price - inp["vwap"]) / atr, 2), "ema9_21_gap_atr": round((inp["ema9"] - inp["ema21"]) / atr, 2),
                "mfe_atr": round(mfe, 2), "mae_atr": round(mae, 2), "exit_move_atr": round(-stop_dist, 2),
                "post30_best_atr": round(post_fav, 2), "target_hit_after_exit": hit_target_later,
                "entry_fill": en.get("fill_price"), "entry_bid": en.get("quote_bid"), "entry_ask": en.get("quote_ask"),
                "exit_fill": ex.get("fill_price"), "exit_bid": ex.get("quote_bid"), "exit_ask": ex.get("quote_ask"),
                "exit_retries": c["retries"], "vol_ratio": round(bs[i0]["v"] / (sum(vol20) / len(vol20)), 2) if vol20 else None,
            })

with open(os.path.join(OUT, "trades.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(trades[0]))
    w.writeheader(); w.writerows(trades)

L = []
def p(*a): L.append(" ".join(str(x) for x in a))
def summ(rows):
    n = len(rows); pn = sum(r["pnl"] for r in rows); wn = sum(r["pnl"] > 0 for r in rows)
    gw = sum(r["pnl"] for r in rows if r["pnl"] > 0); gl = -sum(r["pnl"] for r in rows if r["pnl"] <= 0)
    pf = gw / gl if gl else float("inf")
    return f"{n:3d}t  {pn:+7.0f}  {pn/n if n else 0:+6.1f}/t  win {100*wn/n if n else 0:4.0f}%  avgW {gw/max(wn,1):+5.0f} avgL {-gl/max(n-wn,1):+5.0f}  PF {pf:4.2f}"
def table(title, key, rows=None):
    rows = trades if rows is None else rows
    p(f"== {title}")
    g = defaultdict(list)
    for r in rows: g[key(r)].append(r)
    for k in sorted(g, key=str): p(f"  {str(k):22} {summ(g[k])}")
    p()

p("Five paper days:", ", ".join(DAYS), "- all trades, nothing excluded")
p("ALL", summ(trades)); p()
table("By day", lambda r: r["day"])
table("By strategy", lambda r: r["strategy"])
table("By bot", lambda r: r["bot"])
table("By exit reason", lambda r: r["exit_reason"])
table("By side", lambda r: r["side"])
table("Traded against raw cross (trend_side flip)", lambda r: r["flipped"])
table("By entry hour", lambda r: r["entry_time"][:2])
table("First 15 min (9:30-9:44) vs later", lambda r: "09:30-09:44" if r["entry_time"] < "09:45" else "09:45+")
table("Hold time bucket", lambda r: "0-2m" if r["hold_min"] <= 2 else "3-5m" if r["hold_min"] <= 5 else "6-15m" if r["hold_min"] <= 15 else "16m+")
table("EMA9-21 gap at entry (ATR, signed with side)", lambda r: (lambda g: "<0.25" if g < .25 else "0.25-0.75" if g < .75 else "0.75+")(abs(r["ema9_21_gap_atr"])))
table("Distance from VWAP at entry, signed with trade side (ATR)", lambda r: (lambda d: "against VWAP" if d < 0 else "0-1 with" if d < 1 else "1-2 with" if d < 2 else "2+ with")(r["dist_vwap_atr"] * (1 if r["side"] == "CALL" else -1)))
table("ATR as % of price", lambda r: "<0.06%" if r["atr_pct"] < .06 else "0.06-0.10%" if r["atr_pct"] < .10 else "0.10%+")

p("== Excursion while held (underlying, ATR of signal bar)")
for reason in ("STOP", "TARGET", "TIME"):
    rs = [r for r in trades if r["exit_reason"] == reason]
    if not rs: continue
    p(f"  {reason:6} n={len(rs):3d}  avg MFE {sum(r['mfe_atr'] for r in rs)/len(rs):.2f}  avg MAE {sum(r['mae_atr'] for r in rs)/len(rs):.2f}  "
      f"avg move at exit {sum(r['exit_move_atr'] for r in rs)/len(rs):+.2f}  avg hold {sum(r['hold_min'] for r in rs)/len(rs):.1f}m")
stops = [r for r in trades if r["exit_reason"] == "STOP"]
p(f"  STOP trades that never went +0.5 ATR in favor first: {sum(r['mfe_atr'] < .5 for r in stops)}/{len(stops)}")
p(f"  STOP trades that went +1.0 ATR in favor before stopping: {sum(r['mfe_atr'] >= 1 for r in stops)}/{len(stops)}, P&L {sum(r['pnl'] for r in stops if r['mfe_atr'] >= 1):+.0f}")
p(f"  STOP exits where the close was past 1.5 ATR (overshoot from bar-close stop): {sum(r['exit_move_atr'] <= -1.5 for r in stops)}/{len(stops)}, P&L {sum(r['pnl'] for r in stops if r['exit_move_atr'] <= -1.5):+.0f}")
p(f"  STOP trades where price reached the original +2 ATR target within 30 min after exit: {sum(r['target_hit_after_exit'] for r in stops)}/{len(stops)}")
p(f"  Stopped in 0-2 minutes: {sum(r['hold_min'] <= 2 for r in stops)}/{len(stops)}, P&L {sum(r['pnl'] for r in stops if r['hold_min'] <= 2):+.0f}")
tg = [r for r in trades if r["exit_reason"] == "TARGET"]
p(f"  TARGET trades where price ran a further +1 ATR (to 3+ ATR) within 30 min after exit: {sum(r['post30_best_atr'] >= 3 for r in tg)}/{len(tg)}")
p()

p("== Option fills (cents vs quote at fill)")
ent = [r for r in trades if r["entry_fill"] and r["entry_ask"]]
exi = [r for r in trades if r["exit_fill"] and r["exit_bid"]]
p(f"  entries: avg fill-ask {100*sum(r['entry_fill']-r['entry_ask'] for r in ent)/len(ent):+.2f}c, avg spread {100*sum(r['entry_ask']-r['entry_bid'] for r in ent)/len(ent):.2f}c, n={len(ent)}")
p(f"  exits:   avg fill-bid {100*sum(r['exit_fill']-r['exit_bid'] for r in exi)/len(exi):+.2f}c, n={len(exi)}")
p(f"  spread cost per round trip at 10 contracts ~= ${100*10*sum(r['entry_ask']-r['entry_bid'] for r in ent)/len(ent):.0f}")
p(f"  exits that needed retries: {sum(r['exit_retries']>0 for r in trades)}, P&L {sum(r['pnl'] for r in trades if r['exit_retries']>0):+.0f}")
p()
p("== Entry orders not filled (ORDER_FAILED) by day")
for d in DAYS: p(f"  {d}: {sum(failed[d].values())}  {dict(failed[d])}")
p()
p("== Concurrency: trades opened on the same ticker within 2 minutes by different bots (same idea, stacked size)")
seen = defaultdict(list)
for r in trades: seen[(r["day"], r["ticker"], r["side"])].append(r)
stack = []
for k, rs in seen.items():
    rs.sort(key=lambda r: r["entry_time"])
    for a, b in zip(rs, rs[1:]):
        if (datetime.strptime(b["entry_time"], "%H:%M") - datetime.strptime(a["entry_time"], "%H:%M")).seconds <= 120 and a["bot"] != b["bot"]:
            stack.append((a, b))
p(f"  stacked pairs: {len(stack)}, combined P&L {sum(a['pnl']+b['pnl'] for a,b in stack):+.0f}")
same_minute_all = defaultdict(list)
for r in trades: same_minute_all[(r["day"], r["entry_time"])].append(r)
clusters = [v for v in same_minute_all.values() if len(v) >= 3]
p(f"  minutes with 3+ bots entering at once: {len(clusters)}, trades {sum(len(v) for v in clusters)}, P&L {sum(r['pnl'] for v in clusters for r in v):+.0f}")
p()
p("== Worst 20 trades")
for r in sorted(trades, key=lambda r: r["pnl"])[:20]:
    p(f"  {r['day']} {r['bot']:9} {r['entry_time']}-{r['exit_time']} {r['side']:4} raw {r['raw_cross']:4} {r['exit_reason']:6} {r['pnl']:+6.0f}  "
      f"MFE {r['mfe_atr']:.2f} MAE {r['mae_atr']:.2f} exit {r['exit_move_atr']:+.2f}ATR  gap {r['ema9_21_gap_atr']:+.2f}  retries {r['exit_retries']}")

open(os.path.join(OUT, "output.txt"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
