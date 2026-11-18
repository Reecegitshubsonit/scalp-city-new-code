"""Expanded trade dataset for the 2026-10-09 paper session, built only from logs/2026-10-09-live.jsonl (read-only).
Run from repo root: python3 reports/dissect-2026-10-09/expanded/build.py
Writes, in reports/dissect-2026-10-09/expanded/:
  trades_expanded.csv   one row per closed trade (the original 52, same numbering as signal_table.csv)
  price_paths.csv       ordered underlying 1-minute path for every trade, signal minute to exit-fill minute
  orders_issues.csv     every entry order that did not fill, every exit retry, and orders with no logged outcome
  settings_used.csv     strategy settings in force that day, with the evidence for each
The three positions left open by the 09:58-10:00 restart are excluded from all files (not part of the 52)."""
import collections, csv, json, os, re

LOG = "logs/2026-10-09-live.jsonl"
OUT = "reports/dissect-2026-10-09/expanded/"
DAY = "2026-10-09"
BA = re.compile(r"bid/ask ([\d.]+)/([\d.]+)")
HELD = re.compile(r"stop ([\d.]+), target ([\d.]+)")
RESTART = ("09:58", "10:00")                     # last minute before / first minute after the restart (no events in between)
GAPS = [("11:09", "11:16"), ("11:22", "11:24")]  # feed gaps: minutes with no events at all
TOL = 0.011
ev = [json.loads(l) for l in open(LOG)]


def hm(t): return t[11:16]
def mins(s): return int(s[:2]) * 60 + int(s[3:5])


# ---------- pass 1: per-bot trade assembly ----------
cur, trades, failed, orphans, issues = {}, [], [], [], []
for d in ev:
    b, k, r = d["bot"], d["kind"], d["reason_code"]
    c = cur.get(b)
    if k == "state_change" and r == "SIGNAL":
        if c and c.get("entry_fill"):
            orphans.append(c)                                        # filled, then a new signal: position lost at restart
        elif c and c.get("entry_order") and not c.get("entry_fill") and not c.get("entry_failed"):
            issues.append(dict(kind="ENTRY_NO_OUTCOME", bot=b, time=c["entry_order"]["time"], seq=c["entry_order"]["seq"], contract=c["entry_order"]["contract"],
                               bid=c["entry_bid"], ask=c["entry_ask"], detail="entry order sent; no fill and no failure ever logged"))
        cur[b] = c = dict(bot=b, tk=d["ticker"], signal=d, ticks=[], retries=[], held_text=None)
        continue
    if not c: continue
    if k == "order_sent" and r == "BUY_OPEN":
        m = BA.search(d["reason_text"]); c.update(entry_order=d, entry_bid=float(m[1]), entry_ask=float(m[2]))
    elif k == "state_change" and r == "ORDER_FAILED" and not c.get("entry_fill"):
        c["entry_failed"] = d; failed.append(c); cur.pop(b, None)
        issues.append(dict(kind="ENTRY_NOT_FILLED", bot=b, time=d["time"], seq=d["seq"], contract=c["entry_order"]["contract"], bid=c["entry_bid"], ask=c["entry_ask"], detail=d["reason_text"]))
    elif k == "fill" and r == "ENTRY_FILL":
        c["entry_fill"] = d
    elif k == "tick" and c.get("entry_fill") and not c.get("closed"):
        c["ticks"].append(d)
        mt = HELD.search(d["reason_text"] or "")
        if mt and not c["held_text"]: c["held_text"] = (float(mt[1]), float(mt[2]))
    elif k == "state_change" and r == "EXIT_RETRY":
        c["retries"].append(d)
    elif k == "state_change" and r.startswith("EXIT_"):
        c.setdefault("exit_trigger", d)
    elif k == "order_sent" and r == "SELL_CLOSE":
        m = BA.search(d["reason_text"]); c.setdefault("exit_orders", []).append((d, float(m[1]), float(m[2])))
    elif k == "fill" and r == "EXIT_FILL":
        c["exit_fill"] = d
    elif k == "trade_closed":
        c["closed"] = d; trades.append(c); cur.pop(b, None)
for b, c in cur.items():                                             # end of log
    if c.get("entry_order") and not c.get("entry_fill") and not c.get("entry_failed"):
        issues.append(dict(kind="ENTRY_NO_OUTCOME", bot=b, time=c["entry_order"]["time"], seq=c["entry_order"]["seq"], contract=c["entry_order"]["contract"],
                           bid=c["entry_bid"], ask=c["entry_ask"], detail="entry order sent; no fill and no failure ever logged"))

# minute series per ticker (for paths): every tick carries the underlying's bar close and indicators
series = collections.defaultdict(dict)
for d in ev:
    if d["kind"] == "tick" and d["inputs"].get("price") is not None:
        series[d["ticker"]][hm(d["time"])] = d["inputs"]

# order trades by entry time, same numbering as signal_table.csv (sorted by entry minute, then bot)
trades.sort(key=lambda c: (hm(c["entry_fill"]["time"]), c["bot"]))
assert len(trades) == 52, len(trades)


# ---------- pass 2: rows ----------
def occ(con, tk):
    s = con[len(tk):]; return "20" + s[0:2] + "-" + s[2:4] + "-" + s[4:6], ("CALL" if s[6] == "C" else "PUT"), int(s[7:]) / 1000


rows, paths = [], []
for n, c in enumerate(trades, 1):
    sig, ef, xf, cl = c["signal"], c["entry_fill"], c["exit_fill"], c["closed"]
    tk, con = c["tk"], ef["contract"]
    exp, side, strike = occ(con, tk)
    sg = 1 if side == "CALL" else -1
    i0 = sig["inputs"]; p0, atr = i0["price"], i0["atr"]
    stop_r, tgt_r = round(p0 - sg * atr, 4), round(p0 + sg * 2 * atr, 4)
    stop_l, tgt_l = c["held_text"] if c["held_text"] else (None, None)
    et = c.get("exit_trigger")
    xo = c.get("exit_orders", [])
    last_xo = xo[-1] if xo else (None, None, None)
    in_t, out_t = hm(ef["time"]), hm(xf["time"])
    mid_in, mid_out = (c["entry_bid"] + c["entry_ask"]) / 2, (last_xo[1] + last_xo[2]) / 2
    flags = ["timestamps are 1-minute bar ends, not execution wall-clock"]
    if c["held_text"] is None: flags.append("stop/target not in log text; reconstructed from signal close and ATR")
    if ef.get("quote_bid") is None: flags.append("entry fill record has no quote attached; bid/ask taken from the order_sent line")
    in_ok = c["entry_bid"] - TOL <= ef["fill_price"] <= c["entry_ask"] + TOL
    out_ok = last_xo[1] - TOL <= xf["fill_price"] <= last_xo[2] + TOL
    if not in_ok or not out_ok: flags.append("fill price outside bid/ask (sandbox off-market); logged P&L not reliable, use pnl_at_mids")
    if ef["fill_source"] == "broker_offmarket" or xf["fill_source"] == "broker_offmarket": flags.append("sandbox price outside quote was re-booked at the quote; broker account holds a different price")
    if in_t <= RESTART[0] and out_t >= RESTART[1]: flags.append("position open across the 09:58-10:00 restart")
    for g0, g1 in GAPS:
        if in_t <= g0 and out_t >= g1: flags.append(f"position open across the {g0}-{g1} feed gap (no bars)")
    flags.append("limit price not logged; code places buys at the ask and sells at the bid")
    row = dict(
        trade_id=f"{DAY}-{c['bot']}-{in_t.replace(':', '')}", n=n, bot=c["bot"], ticker=tk, trigger=c["bot"].split("-")[1], side=side,
        option_symbol=con, expiration=exp, strike=strike, qty_ordered=c["entry_order"]["qty"], qty_filled_entry=ef["qty"], qty_filled_exit=xf["qty"],
        signal_time=hm(sig["time"]), signal_seq=sig["seq"], signal_und_close=p0, atr_at_signal=atr, charge_pct_at_signal=sig.get("charge_pct"),
        vwap_at_signal=i0.get("vwap"), ema9_at_signal=i0.get("ema9"), ema21_at_signal=i0.get("ema21"), ema50_at_signal=i0.get("ema50"),
        stop_und_logged=stop_l, target_und_logged=tgt_l, stop_und_reconstructed=stop_r, target_und_reconstructed=tgt_r,
        entry_order_time=hm(c["entry_order"]["time"]), entry_order_seq=c["entry_order"]["seq"], entry_bid=c["entry_bid"], entry_ask=c["entry_ask"],
        entry_fill_time=in_t, entry_fill_seq=ef["seq"], entry_fill_price=ef["fill_price"], entry_fill_source=ef["fill_source"], entry_fill_in_quote=in_ok,
        und_at_entry_fill=ef["inputs"].get("price"),
        exit_trigger=et["reason_code"].replace("EXIT_", "") if et else "", exit_trigger_time=hm(et["time"]) if et else "", exit_trigger_und_close=et["inputs"].get("price") if et else "",
        exit_orders_sent=len(xo), exit_retries=len(c["retries"]), exit_retry_times=";".join(hm(x["time"]) for x in c["retries"]),
        exit_order_time=hm(last_xo[0]["time"]) if xo else "", exit_bid=last_xo[1], exit_ask=last_xo[2],
        exit_fill_time=out_t, exit_fill_seq=xf["seq"], exit_fill_price=xf["fill_price"], exit_fill_source=xf["fill_source"], exit_fill_in_quote=out_ok,
        und_at_exit_fill=xf["inputs"].get("price"), exit_R_und=round(sg * (xf["inputs"]["price"] - p0) / atr, 3),
        hold_min=mins(out_t) - mins(in_t), pnl_logged=cl["pnl"], pnl_at_mids=round((mid_out - mid_in) * ef["qty"] * 100), bot_pnl_day_after=cl["pnl_day"],
        bot_trade_count_after=cl["trades"], close_state=cl["reason_code"],
        fee_logged=ef.get("fee"),
        opposing_overlap="", same_side_overlap="", flags=" | ".join(flags))
    rows.append(row)
    # path
    for t in sorted(series[tk]):
        if hm(sig["time"]) <= t <= out_t:
            x = series[tk][t]
            ph = "signal" if t == hm(sig["time"]) else "exit fill" if t == out_t else "holding"
            if et and t == hm(et["time"]) and t != out_t: ph = "exit trigger"
            paths.append(dict(trade_id=row["trade_id"], n=n, minute=t, phase=ph, und_close=x["price"], vwap=x.get("vwap"), ema9=x.get("ema9"), ema21=x.get("ema21"),
                              ema50=x.get("ema50"), atr=x.get("atr"), move_R=round(sg * (x["price"] - p0) / atr, 3),
                              dist_to_stop_R=round(sg * (x["price"] - stop_r) / atr, 3), dist_to_target_R=round(sg * (tgt_r - x["price"]) / atr, 3)))
    for r_ in c["retries"]:
        issues.append(dict(kind="EXIT_RETRY", bot=c["bot"], time=r_["time"], seq=r_["seq"], contract=con, bid="", ask="", detail=r_["reason_text"], trade_id=row["trade_id"]))

# overlaps: other bot, same ticker, positions open at the same time (entry fill minute to exit fill minute, open interval)
for a in rows:
    opp, same = [], []
    for b in rows:
        if a is b or a["ticker"] != b["ticker"] or a["bot"] == b["bot"]: continue
        if b["entry_fill_time"] < a["exit_fill_time"] and a["entry_fill_time"] < b["exit_fill_time"]:
            (opp if b["side"] != a["side"] else same).append(f"#{b['n']} {b['bot']} {b['side']}")
    a["opposing_overlap"] = "; ".join(opp); a["same_side_overlap"] = "; ".join(same)
    if opp: a["flags"] += " | overlapped an opposite-side position on the same ticker (unintended)"

cols = list(rows[0])
with open(OUT + "trades_expanded.csv", "w", newline="") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
with open(OUT + "price_paths.csv", "w", newline="") as f:
    w = csv.DictWriter(f, list(paths[0])); w.writeheader(); w.writerows(paths)
issues.sort(key=lambda x: x["seq"])
for x in issues:
    x["time"] = hm(x["time"])
    if x["kind"] == "ENTRY_NO_OUTCOME": x["detail"] += "; likely the 10 extra QQQ 749 puts found in the broker account (unconfirmed)"
with open(OUT + "orders_issues.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["kind", "time", "seq", "bot", "contract", "bid", "ask", "trade_id", "detail"], extrasaction="ignore"); w.writeheader(); w.writerows(issues)

# ---------- settings in force ----------
def first(pred): return next((d for d in ev if pred(d)), None)
locks = [(hm(d["time"]), d["bot"], d["pnl_day"]) for d in ev if d["kind"] == "trade_closed" and d["reason_code"] == "DAILY_LOSS"]
unlocked = [(hm(d["time"]), d["bot"], d["pnl_day"]) for d in ev if d["kind"] == "trade_closed" and d["reason_code"] == "COOLDOWN"]
pre = [x for x in unlocked if x[0] < "10:00"]; post = [x for x in unlocked if x[0] >= "10:00"]
lock_pre = [x for x in locks if x[0] < "10:00"]; lock_post = [x for x in locks if x[0] >= "10:00"]
cool = first(lambda d: d["reason_code"] == "COOLDOWN" and d["kind"] == "state_change")
side_cross = sum(1 for c in trades if c["bot"].split("-")[1] in ("VWAP", "EMA50"))
settings = [
    ("contracts per trade", "10", "every order_sent and fill has qty 10", "confirmed"),
    ("option", "ATM strike, next trading day expiry (Mon 2026-10-12)", "every contract symbol", "confirmed"),
    ("stop / target", "1 ATR / 2 ATR from the signal close, checked on bar close", "stop/target text in HOLDING ticks matches signal close +/- ATR", "confirmed"),
    ("side rule", "raw cross / break direction (trend_side NOT active)", f"all {side_cross} VWAP and EMA50 trades took the cross direction; trend_side was added to config.py at 15:16 ET, after start", "confirmed"),
    ("chop (squeeze) filter", "VWAP bots only, |EMA9-EMA21| < 0.15 ATR", "CHOP_SQUEEZE events only on IWM/SPY/QQQ-VWAP", "confirmed (threshold from code, not visible in log)"),
    ("cooldown", "2 minutes", f"'{cool['reason_text']}' at {hm(cool['time'])}", "confirmed"),
    ("last entry / flat", "15:30 / 15:55", "OUTSIDE_WINDOW 'after last entry 15:30'; flat time from code (no position open at 15:55)", "15:30 confirmed; 15:55 from code"),
    ("range window", "9:30-9:44 bars, signals from 9:45", "RANGE_FORMING 'armed, range forming until 09:45'", "confirmed"),
    ("daily loss lock, before restart", "between $130 and $250 (inferred)", f"locked: {lock_pre}; not locked at: {[x for x in pre if x[2] < 0]}", "uncertain: exact value not logged"),
    ("daily loss lock, after restart", "between $720 and $960 (inferred)", f"locked: {lock_post}; deepest not locked: {min(post, key=lambda x: x[2])}", "uncertain: exact value not logged; differs from config default $100"),
    ("daily goal lock", "above $310 (no goal lock fired)", f"highest pnl_day without a lock: {max(unlocked, key=lambda x: x[2])}", "uncertain: config default $600"),
    ("day P&L reset at restart", "yes for QQQ-EMA50, QQQ-RANGE, IWM-RANGE", "first trade after restart shows trades=1 and pnl_day equal to that trade", "confirmed"),
    ("off-market fill check", "active after the restart only", "broker_offmarket fills only from 10:02; off-market prices booked as-is before 10:00", "confirmed"),
    ("code version", "uncommitted working tree; exact version at start not recorded", "config.py and bot.py modified 15:16 ET", "uncertain"),
    ("probable second restart 11:09-11:16", "different code before and after the 11:09-11:16 gap", "no events for 7 minutes; fill records carry quote_bid/quote_ask only from 11:27 (exit) / 11:32 (entry); day P&L carried over correctly", "uncertain: inferred, not logged"),
]
with open(OUT + "settings_used.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["setting", "value in force", "evidence from the log", "status"]); w.writerows(settings)
print(f"{len(rows)} trades, {len(paths)} path rows, {len(issues)} order issues, {len(orphans)} restart positions excluded")
print("opposing overlaps:", sum(1 for r in rows if r["opposing_overlap"]))
