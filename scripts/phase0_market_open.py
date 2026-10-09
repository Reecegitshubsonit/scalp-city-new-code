"""Phase-0 checks for market hours (run ~10:00 ET on a trading day, in manual permission mode).

1. Option quote freshness: polls 3 contracts for 60 s, prints quote age and delay flag.
2. Option order path: places ONE resting 1-contract limit far below the market, waits 30 s, cancels.
3. --place saves the resting-order detail JSON to tests/fixtures/webull/.
4. --fill-test buys 1 SPY call at the ask, waits for the fill, sells it back at the bid, and saves both filled
   order-detail JSONs so FILLED_PRICE_KEYS / FILLED_QTY_KEYS can be confirmed.
Run: python scripts/phase0_market_open.py [--place] [--fill-test]
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.contracts import atm_strike, next_trading_day, occ_symbol
from scalpcity.guard import SANDBOX_HOST, assert_paper_only
from scalpcity.types import ET
from scalpcity.webull_client import WebullClient


def load_env(path=".env"):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def wait_filled(client, account_id, order_id, seconds=30):
    detail = None
    for _ in range(seconds):
        detail = client.order_detail(account_id, order_id)
        if detail["orders"][0]["status"].upper() == "FILLED":
            break
        time.sleep(1)
    return detail


def fill_test(client, account_id, contract):
    """Sandbox only: marketable BUY 1 at the ask, wait for FILLED, then SELL 1 at the bid and wait."""
    quote, _ = client.option_quote(contract)
    print(f"buying 1 {contract} at the ask {quote.ask}")
    buy_id = client.place_option(account_id, contract, "BUY", 1, quote.ask)
    buy = wait_filled(client, account_id, buy_id)
    quote, _ = client.option_quote(contract)
    print(f"selling 1 {contract} at the bid {quote.bid}")
    sell_id = client.place_option(account_id, contract, "SELL", 1, quote.bid)
    sell = wait_filled(client, account_id, sell_id)
    os.makedirs("tests/fixtures/webull", exist_ok=True)
    json.dump({"buy": buy, "sell": sell}, open("tests/fixtures/webull/option_filled_order_detail.json", "w"), indent=1)
    print("buy status:", buy["orders"][0]["status"], "| sell status:", sell["orders"][0]["status"])
    print("fields on the filled order:", sorted(buy["orders"][0].keys()))


def main():
    load_env()
    client = WebullClient.from_env(os.environ)
    account = assert_paper_only(os.environ, SANDBOX_HOST, client.accounts())
    now = datetime.now(ET)
    expiry = next_trading_day(now.date())
    contracts = {}
    for t in ("QQQ", "SPY", "IWM"):
        bars = client.recent_bars(t, 1)
        contracts[t] = occ_symbol(t, expiry, "CALL", atm_strike(bars[-1].close))
    print("contracts:", contracts)
    print("--- quote freshness, 12 polls over 60 s ---")
    for i in range(12):
        row = []
        for t, c in contracts.items():
            got = client.option_quote(c)
            if got is None:
                row.append(f"{t}: none")
                continue
            quote, delay = got
            age = (datetime.now(ET) - quote.ts).total_seconds()
            row.append(f"{t}: {quote.bid}/{quote.ask} age={age:.1f}s delay={delay}m")
        print(datetime.now(ET).strftime("%H:%M:%S"), " | ".join(row))
        time.sleep(5)
    if "--place" not in sys.argv and "--fill-test" not in sys.argv:
        print("quote check only. Re-run with --place (resting order) or --fill-test (buy and sell back 1 contract).")
        return
    contract = contracts["SPY"]
    if "--fill-test" in sys.argv:
        fill_test(client, account["account_id"], contract)
        return
    got = client.option_quote(contract)
    print("placing 1 SPY call limit 0.05 (market ~", got[0].ask if got else "?", ") then cancelling after 30 s")
    oid = client.place_option(account["account_id"], contract, "BUY", 1, 0.05)
    detail1 = client.order_detail(account["account_id"], oid)
    time.sleep(30)
    detail2 = client.order_detail(account["account_id"], oid)
    client.cancel_option(account["account_id"], oid)
    detail3 = client.order_detail(account["account_id"], oid)
    os.makedirs("tests/fixtures/webull", exist_ok=True)
    json.dump({"submitted": detail1, "after_30s": detail2, "cancelled": detail3}, open("tests/fixtures/webull/option_order_detail.json", "w"), indent=1)
    print("saved tests/fixtures/webull/option_order_detail.json; statuses:",
          [d["orders"][0]["status"] for d in (detail1, detail2, detail3)])


if __name__ == "__main__":
    main()
