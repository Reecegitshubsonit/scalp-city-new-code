"""SANDBOX-ONLY order path test: list accounts, preview, place, query, cancel ONE resting 1-contract option order.

The limit price is far below the market so it cannot fill. Refuses to run unless host is the sandbox host.
Run from ~/scalp-city:  .venv/bin/python probe/order_test.py [--place]
Without --place it only previews (nothing is sent as an order).
Output masks account ids. Raw responses (ids masked) go to probe/raw/.
"""
import datetime as dt
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX_HOST = "api.sandbox.webull.com"
UNDERLYING = "SPY"
LIMIT_PRICE = "0.05"   # SPY 1DTE ATM call trades ~$2; this cannot fill


def load_env(path):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def mask(value):
    s = str(value)
    return "…" + s[-4:] if len(s) > 4 else "…"


def body(response):
    try:
        return response.json()
    except Exception:
        return {"_raw": str(getattr(response, "text", response))[:400]}


def scrub(obj):
    """Mask anything that looks like an account id before saving or printing."""
    if isinstance(obj, dict):
        return {k: (mask(v) if "account" in k.lower() and "type" not in k.lower() and "class" not in k.lower() and isinstance(v, (str, int)) else scrub(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj


def save(name, obj):
    os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)
    with open(os.path.join(HERE, "raw", name + ".json"), "w") as handle:
        json.dump(scrub(obj), handle, indent=1, default=str)


def show(label, response):
    j = body(response)
    save(label, j)
    print(f"{label}: http={getattr(response, 'status_code', '?')}  {json.dumps(scrub(j))[:420]}")
    return j


def main():
    load_env(os.path.join(os.path.dirname(HERE), ".env"))
    if os.environ.get("WEBULL_ENV", "").lower() != "sandbox" or os.environ.get("WEBULL_SANDBOX_ACCOUNT_ATTESTED", "").lower() != "true":
        sys.exit("refusing: WEBULL_ENV must be sandbox and WEBULL_SANDBOX_ACCOUNT_ATTESTED must be true")
    from webull.core.client import ApiClient
    from webull.data.data_client import DataClient
    from webull.trade.trade_client import TradeClient

    api = ApiClient(os.environ["WEBULL_APP_KEY"], os.environ["WEBULL_APP_SECRET"], "us")
    api.add_endpoint("us", SANDBOX_HOST)
    api._stream_logger_set = True
    api._file_logger_set = True
    data, trade = DataClient(api), TradeClient(api)
    print("host:", SANDBOX_HOST)

    # 1. accounts
    accounts = show("accounts", trade.account_v2.get_account_list())
    rows = accounts if isinstance(accounts, list) else accounts.get("data") or accounts.get("accounts") or []
    print(f"accounts found: {len(rows)}")
    wanted = os.environ.get("WEBULL_PAPER_ACCOUNT_NUMBER", "")
    match = [r for r in rows if wanted and r.get("account_number") == wanted]
    if len(match) != 1:
        sys.exit("saved WEBULL_PAPER_ACCOUNT_NUMBER matches %d accounts; stopping so we don't guess" % len(match))
    account_id = match[0]["account_id"]
    print("using account", mask(account_id), match[0].get("account_class"), match[0].get("account_type"))

    # 2. price + contract
    bars = body(data.market_data.get_history_bar(UNDERLYING, "US_STOCK", "M1", count="1", real_time_required=True, trading_sessions="PRE,RTH"))
    node = bars
    while isinstance(node, (dict, list)) and "close" not in (node if isinstance(node, dict) else {}):
        node = node[0] if isinstance(node, list) else node["result"]
    last = float(node["close"])
    strike = round(last)
    expiry = dt.date.today() + dt.timedelta(days=1)
    while expiry.weekday() >= 5:
        expiry += dt.timedelta(days=1)
    occ = f"{UNDERLYING}{expiry:%y%m%d}C{int(strike * 1000):08d}"
    snap = body(data.option_market_data.get_option_snapshot(occ, "US_OPTION"))
    row = snap[0] if isinstance(snap, list) else snap
    print(f"contract {occ}  bid/ask {row.get('bid')}/{row.get('ask')}  (order limit {LIMIT_PRICE} cannot fill)")

    client_order_id = uuid.uuid4().hex[:32]
    order = [{
        "client_order_id": client_order_id,
        "combo_type": "NORMAL",
        "order_type": "LIMIT",
        "quantity": "1",
        "limit_price": LIMIT_PRICE,
        "option_strategy": "SINGLE",
        "side": "BUY",
        "time_in_force": "GTC",
        "entrust_type": "QTY",
        "orders": [{
            "side": "BUY", "quantity": "1", "symbol": UNDERLYING, "strike_price": f"{strike:.1f}",
            "init_exp_date": str(expiry), "instrument_type": "OPTION", "option_type": "CALL", "market": "US",
        }],
    }]

    # 3. preview (sends nothing); place + cancel only with --place
    show("order_preview", trade.order_v2.preview_option(account_id, order))
    if "--place" not in sys.argv:
        print("preview only (no order placed). Re-run with --place to place and cancel one resting order.")
        return
    try:
        show("order_place", trade.order_v2.place_option(account_id, order))
        show("order_detail_1", trade.order_v2.get_order_detail(account_id, client_order_id))
    finally:
        try:
            show("order_cancel", trade.order_v2.cancel_option(account_id, client_order_id))
            show("order_detail_2", trade.order_v2.get_order_detail(account_id, client_order_id))
        except Exception as error:
            print("cancel/detail error:", str(error)[:300])
    print("Done.")


if __name__ == "__main__":
    main()
