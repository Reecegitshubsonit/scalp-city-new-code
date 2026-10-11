"""Entry-filter backtest on the underlying: the 3 Scalp City triggers with and without extra entry filters.
Research script, paper only, reads backtest/data/*_1m.json (no network). Results are in R (1R = the 1 ATR stop).
Live rules mirrored: entries 9:30-15:30 (range bot from 9:45), stop 1 ATR, target 2 ATR, flat 15:55, 2 min cooldown,
VWAP bot skips EMA9/EMA21 squeezes. Stop is checked before target inside a bar (conservative). No daily loss/goal limits."""
import json, collections, statistics as st
from datetime import datetime, time as T, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
TICKERS = ("SPY", "QQQ", "IWM")
LAST_ENTRY, FLAT, COOL = T(15, 30), T(15, 55), 2
COST_R = 0.2   # sensitivity: option spread/theta drag per trade, in R


def load(t):
    out = []
    for b in json.load(open(f"backtest/data/{t}_1m.json")):
        s = datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET)
        if T(9, 30) <= s.time() < T(16, 0):
            out.append((s, b["o"], b["h"], b["l"], b["c"], b["v"]))
    return out


class Ema:
    def __init__(s, n): s.k = 2 / (n + 1); s.v = None
    def u(s, x): s.v = x if s.v is None else s.v + s.k * (x - s.v); return s.v


def prepare(bars):
    """Per bar: indicators and each trigger's baseline signal."""
    e9, e21, e50 = Ema(9), Ema(21), Ema(50)
    atr = None; pc = None; n = 0; day = None; pv = vv = 0.0
    prev = {"vwap": None, "ema50": None}
    hi = lo = None; inrange_prev = True
    rows = []
    for i, (s, o, h, l, c, v) in enumerate(bars):
        if s.date() != day:
            day = s.date(); pv = vv = 0.0; prev = {"vwap": None, "ema50": None}; hi, lo = -1e9, 1e9; inrange_prev = True
        tr = (h - l) if pc is None else max(h - l, abs(h - pc), abs(l - pc)); pc = c; n += 1
        atr = tr if atr is None else (atr * 13 + tr) / 14 if n > 14 else (atr * (n - 1) + tr) / n
        a9, a21, a50 = e9.u(c), e21.u(c), e50.u(c)
        tp = (h + l + c) / 3; pv += tp * v; vv += v; vwap = pv / vv
        r = dict(i=i, t=s, c=c, atr=atr, e9=a9, e21=a21, sig={}, side={}, dist={})
        for k, lvl in (("vwap", vwap), ("ema50", a50)):
            side = (c > lvl) - (c < lvl); p = prev[k]
            r["side"][k] = side; r["dist"][k] = abs(c - lvl) / atr if atr else 0.0
            if p is not None and side != 0 and p != 0 and side != p:
                r["sig"][k] = "CALL" if side > 0 else "PUT"
            if side != 0: prev[k] = side
            elif p is None: prev[k] = 0
        if s.time() < T(9, 45):
            hi = max(hi, h); lo = min(lo, l)
        else:
            inside = lo <= c <= hi
            if inrange_prev and not inside:
                r["sig"]["range"] = "CALL" if c > hi else "PUT"
                r["dist"]["range"] = (c - hi if c > hi else lo - c) / atr if atr else 0.0
            inrange_prev = inside
        rows.append(r)
    return rows


def signal(rows, k, bot, cfg):
    """Return 'CALL'/'PUT'/None for bar k under this variant."""
    x = rows[k]; d = x["sig"].get(bot)
    if cfg.get("confirm") and k > 0:
        pd = rows[k - 1]["sig"].get(bot)
        if not pd: return None
        if bot == "range":   # the next close keeps going the same way as the breakout bar
            ok = (x["c"] > rows[k - 1]["c"]) if pd == "CALL" else (x["c"] < rows[k - 1]["c"])
        else:                # the next close is still on the new side of the line
            ok = x["side"][bot] == (1 if pd == "CALL" else -1)
        d = pd if ok else None
    elif not d:
        return None
    buf = cfg.get("buffer", 0.0)
    if buf and d:
        dist = x["dist"].get(bot, 0.0)
        if dist < buf: return None
    if d and cfg.get("trend"):
        if (d == "CALL") != (x["e9"] > x["e21"]): return None
    chop = abs(x["e9"] - x["e21"]) < 0.15 * x["atr"]
    if d and chop and (bot == "vwap" or cfg.get("chop_all")): return None
    return d


def run(t, rows, cfg):
    trades = []
    byday = collections.defaultdict(list)
    for r in rows: byday[r["t"].date()].append(r)
    for day, xs in byday.items():
        for bot in ("vwap", "ema50", "range"):
            k = 0; free_at = None; block = None   # block = direction blocked after a stop
            while k < len(xs) - 1:
                x = xs[k]; end = x["t"] + timedelta(minutes=1)
                if end.time() > LAST_ENTRY or (bot == "range" and end.time() < T(9, 45)) or (free_at and end < free_at):
                    k += 1; continue
                sig = signal(xs, k, bot, cfg)
                if not sig: k += 1; continue
                if cfg.get("noreentry") and block == sig: k += 1; continue
                if cfg.get("noreentry") and block and block != sig: block = None
                ent = x["c"]; atr = x["atr"]
                sa, ta = cfg.get("stop", 1.0), cfg.get("tgt", 2.0)   # stop and target distance in ATR; R is in ATR units
                stop = ent - sa * atr if sig == "CALL" else ent + sa * atr; tgt = ent + ta * atr if sig == "CALL" else ent - ta * atr
                j = k + 1; why = "TIME"; R = 0.0; exit_end = None
                while j < len(xs):
                    y = xs[j]; h, l, c = bars_hl[(t, y["i"])]
                    yend = y["t"] + timedelta(minutes=1)
                    hit_s = l <= stop if sig == "CALL" else h >= stop
                    hit_t = h >= tgt if sig == "CALL" else l <= tgt
                    if hit_s: why, R, exit_end = "STOP", -sa, yend; break
                    if hit_t: why, R, exit_end = "TARGET", ta, yend; break
                    if yend.time() >= FLAT or j == len(xs) - 1:
                        R = ((c - ent) if sig == "CALL" else (ent - c)) / atr; exit_end = yend; break
                    j += 1
                trades.append(dict(t=t, bot=bot, day=day, R=R, why=why, dir=sig))
                if why == "STOP": block = sig
                free_at = exit_end + timedelta(minutes=COOL)
                while k < len(xs) and xs[k]["t"] + timedelta(minutes=1) < free_at: k += 1
    return trades


bars_hl = {}
VARIANTS = [
    ("baseline (live rules)", {}),
    ("close buffer 0.2 ATR", dict(buffer=0.2)),
    ("close buffer 0.4 ATR", dict(buffer=0.4)),
    ("2 closes past line", dict(confirm=True)),
    ("chop filter on all bots", dict(chop_all=True)),
    ("no same-dir re-entry after stop", dict(noreentry=True)),
    ("trend align (EMA9 vs EMA21)", dict(trend=True)),
    ("buffer 0.2 + chop all", dict(buffer=0.2, chop_all=True)),
    ("2 closes + chop all", dict(confirm=True, chop_all=True)),
    ("buffer 0.2 + trend + chop all", dict(buffer=0.2, trend=True, chop_all=True)),
]


def summarize(tr):
    if not tr: return "no trades"
    R = [x["R"] for x in tr]; w = sum(1 for r in R if r > 0)
    return f"{len(R):5d} tr  win {100*w/len(R):4.1f}%  avgR {st.mean(R):+.3f}  totR {sum(R):+7.1f}  avgR-{COST_R}cost {st.mean(R)-COST_R:+.3f}"


if __name__ == "__main__":
    allrows = {}
    for t in TICKERS:
        bars = load(t)
        for i, (s, o, h, l, c, v) in enumerate(bars): bars_hl[(t, i)] = (h, l, c)
        allrows[t] = prepare(bars)
    days = sorted({r["t"].date() for r in allrows["SPY"]})
    print(f"days {days[0]}..{days[-1]} ({len(days)}), tickers {TICKERS}, 3 bots each\n")
    mid = days[len(days) // 2]
    for name, cfg in VARIANTS:
        tr = [x for t in TICKERS for x in run(t, allrows[t], cfg)]
        print(f"{name:34s} {summarize(tr)}")
        for bot in ("vwap", "ema50", "range"):
            print(f"   {bot:6s} {summarize([x for x in tr if x['bot']==bot])}")
        a = [x for x in tr if x["day"] < mid]; b = [x for x in tr if x["day"] >= mid]
        print(f"   1st half {summarize(a)}\n   2nd half {summarize(b)}")
