"""SANDBOX-ONLY ETF order test: preview, then (with --place) place, wait 30 s, query and cancel ONE resting 1-share limit order.

The limit is far below the market ($1.00 vs SPY ~$770) so it cannot fill.
Run from ~/scalp-city:  .venv/bin/python probe/etf_order_test.py [--place]
Without --place it only previews (nothing is sent as an order). Account ids are masked in output.
"""
import json
import os
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX_HOST = "api.sandbox.webull.com"
SYMBOL = "SPY"
LIMIT_PRICE = "1.00"


def load_env(path):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def mask(value):
    s = str(value)
    return "…" + s[-4:] if len(s) > 4 else "…"


def show(label, response):
    try:
        j = response.json()
    except Exception:
        j = {"_raw": str(getattr(response, "text", response))[:300]}
    print(f"{label}: http={getattr(response, 'status_code', '?')}  {json.dumps(j)[:420]}")
    return j


def main():
    load_env(os.path.join(os.path.dirname(HERE), ".env"))
    if os.environ.get("WEBULL_ENV", "").lower() != "sandbox" or os.environ.get("WEBULL_SANDBOX_ACCOUNT_ATTESTED", "").lower() != "true":
        sys.exit("refusing: WEBULL_ENV must be sandbox and WEBULL_SANDBOX_ACCOUNT_ATTESTED must be true")
    from webull.core.client import ApiClient
    from webull.trade.trade_client import TradeClient

    api = ApiClient(os.environ["WEBULL_APP_KEY"], os.environ["WEBULL_APP_SECRET"], "us")
    api.add_endpoint("us", SANDBOX_HOST)
    api._stream_logger_set = True
    api._file_logger_set = True
    trade = TradeClient(api)
    print("host:", SANDBOX_HOST)

    rows = trade.account_v2.get_account_list().json()
    rows = rows if isinstance(rows, list) else rows.get("data") or []
    wanted = os.environ.get("WEBULL_PAPER_ACCOUNT_NUMBER", "")
    match = [r for r in rows if wanted and r.get("account_number") == wanted]
    if len(match) != 1:
        sys.exit("saved WEBULL_PAPER_ACCOUNT_NUMBER matches %d accounts; stopping" % len(match))
    account_id = match[0]["account_id"]
    print("using account", mask(account_id), match[0].get("account_class"))

    client_order_id = uuid.uuid4().hex[:32]
    order = [{
        "client_order_id": client_order_id,
        "symbol": SYMBOL,
        "instrument_type": "EQUITY",
        "market": "US",
        "order_type": "LIMIT",
        "limit_price": LIMIT_PRICE,
        "quantity": "1",
        "support_trading_session": "ALL",
        "side": "BUY",
        "time_in_force": "DAY",
        "entrust_type": "QTY",
    }]

    show("preview", trade.order_v2.preview_order(account_id, order))
    if "--place" not in sys.argv:
        print("preview only (no order placed). Re-run with --place to place and cancel one resting order.")
        return
    try:
        show("place", trade.order_v2.place_order(account_id, order))
        show("detail_1", trade.order_v2.get_order_detail(account_id, client_order_id))
        print("waiting 30 seconds before cancelling...", flush=True)
        time.sleep(30)
        show("detail_after_30s", trade.order_v2.get_order_detail(account_id, client_order_id))
    finally:
        try:
            show("cancel", trade.order_v2.cancel_order_v2(account_id, client_order_id))
            show("detail_2", trade.order_v2.get_order_detail(account_id, client_order_id))
        except Exception as error:
            print("cancel/detail error:", str(error)[:300])
    print("Done.")


if __name__ == "__main__":
    main()
