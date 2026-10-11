"""READ-ONLY Webull probe. Data calls only: no orders, no account endpoints.

Run from ~/scalp-city:  .venv/bin/python probe/probe_webull.py
Prints a summary with no keys and no account numbers. Raw responses go to probe/raw/.
"""
import datetime as dt
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX_HOST = "api.sandbox.webull.com"   # US sandbox host per developer.webull.com/apis/docs/sdk
TICKERS = ["QQQ", "SPY", "IWM"]


def load_env(path):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def body(response):
    try:
        return response.json()
    except Exception:
        return {"_raw": str(getattr(response, "text", response))[:500]}


def save(name, obj):
    os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)
    with open(os.path.join(HERE, "raw", name + ".json"), "w") as handle:
        json.dump(obj, handle, indent=1, default=str)


def find(obj, *names):
    """First value found for any of `names` anywhere in a nested dict/list."""
    if isinstance(obj, dict):
        for n in names:
            if n in obj and obj[n] not in (None, ""):
                return obj[n]
        for v in obj.values():
            r = find(v, *names)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find(v, *names)
            if r is not None:
                return r
    return None


def next_trading_day(day):
    d = day + dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d   # holidays not handled; the probe reports if the contract is missing


def main():
    load_env(os.path.join(os.path.dirname(HERE), ".env"))
    if os.environ.get("WEBULL_ENV", "").lower() != "sandbox" or os.environ.get("WEBULL_SANDBOX_ACCOUNT_ATTESTED", "").lower() != "true":
        sys.exit("refusing: WEBULL_ENV must be sandbox and WEBULL_SANDBOX_ACCOUNT_ATTESTED must be true")
    from webull.core.client import ApiClient
    from webull.data.data_client import DataClient

    api = ApiClient(os.environ["WEBULL_APP_KEY"], os.environ["WEBULL_APP_SECRET"], "us")
    api.add_endpoint("us", SANDBOX_HOST)
    api._stream_logger_set = True   # skip SDK console/file logging so no request headers are printed
    api._file_logger_set = True
    data = DataClient(api)
    now = dt.datetime.now(dt.timezone.utc)
    print(f"host: {SANDBOX_HOST}   now(UTC): {now:%H:%M:%S}")

    price = {}
    for sym in TICKERS:
        print(f"\n== {sym} stock 1-minute bars")
        try:
            r = data.market_data.get_history_bar(sym, "US_STOCK", "M1", count="5", real_time_required=True, trading_sessions="PRE,RTH")
            j = body(r)
            save(f"{sym}_bars", j)
            rows = j if isinstance(j, list) else find(j, "result", "data", "bars") or []
            print(f"http={getattr(r, 'status_code', '?')} bars={len(rows) if isinstance(rows, list) else 'n/a'}")
            if isinstance(rows, list) and rows:
                last = rows[0] if isinstance(rows[0], dict) else {}
                print("fields:", sorted(last.keys()))
                t = find(last, "time", "t", "timestamp")
                print("newest bar time:", t)
                c = find(last, "close", "c")
                if c is not None:
                    price[sym] = float(c)
            elif not isinstance(rows, list) or not rows:
                print("no rows; response head:", json.dumps(j)[:300])
        except Exception as error:
            print("ERROR:", str(error)[:300])

    expiry = next_trading_day(dt.datetime.now().date())
    print(f"\n1DTE expiry used: {expiry} (weekday math only; holidays not handled)")
    for sym in TICKERS:
        if sym not in price:
            print(f"\n== {sym} options: skipped (no underlying price)")
            continue
        strike = round(price[sym])
        print(f"\n== {sym} options: ATM strike {strike}")
        try:
            r = data.instrument.list_option_contracts(underlying_symbols=sym, start_date=str(expiry), strike_price_gte=str(strike), strike_price_lte=str(strike)) \
                if hasattr(data.instrument, "list_option_contracts") else None
            j = body(r) if r is not None else {}
            save(f"{sym}_contracts", j)
            print("contracts response head:", json.dumps(j)[:300])
        except Exception as error:
            print("contracts ERROR:", str(error)[:300])
        occ = {side: f"{sym}{expiry:%y%m%d}{side}{int(strike * 1000):08d}" for side in ("C", "P")}
        for side, symbol in occ.items():
            try:
                r = data.option_market_data.get_option_snapshot(symbol, "US_OPTION")
                j = body(r)
                save(f"{symbol}_snapshot", j)
                print(f"{symbol} snapshot http={getattr(r, 'status_code', '?')}")
                print("  bid/ask:", find(j, "bid", "bid_price", "b"), "/", find(j, "ask", "ask_price", "a"),
                      " iv:", find(j, "implied_volatility", "iv"), " delta:", find(j, "delta"),
                      " time:", find(j, "trade_time", "quote_time", "time", "timestamp"))
                if find(j, "bid", "bid_price", "b") is None:
                    print("  response head:", json.dumps(j)[:300])
            except Exception as error:
                print(f"{symbol} snapshot ERROR:", str(error)[:300])
            try:
                r = data.option_market_data.get_option_history_bars(symbol, "US_OPTION", "M1", count="5")
                j = body(r)
                save(f"{symbol}_bars", j)
                rows = find(j, "result", "data", "bars") if not isinstance(j, list) else j
                print(f"  option bars: {len(rows) if isinstance(rows, list) else 'n/a'}")
            except Exception as error:
                print("  option bars ERROR:", str(error)[:300])
            time.sleep(0.4)
    print("\nDone. Read-only. Raw responses in probe/raw/.")


if __name__ == "__main__":
    main()
