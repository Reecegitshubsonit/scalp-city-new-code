"""READ-ONLY: list today's option orders from the Webull sandbox and compare real fill prices with what the event log recorded.
Run: .venv/bin/python scripts/verify_fills.py   (prints no keys; account id masked)"""
import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scalpcity.guard import SANDBOX_HOST, assert_paper_only
from scalpcity.types import ET
from scalpcity.webull_client import WebullClient

def load_env(path=".env"):
    for raw in open(path):
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values(): yield from walk(v)
    elif isinstance(o, list):
        for v in o: yield from walk(v)

def main():
    load_env()
    client = WebullClient.from_env(os.environ)
    acct = assert_paper_only(os.environ, SANDBOX_HOST, client.accounts())
    today = datetime.now(ET).date().isoformat()
    resp = client._call(client.trade.order_v2.get_order_history, acct["account_id"], page_size=100)
    body = resp.json() if hasattr(resp, "json") else resp
    os.makedirs("logs", exist_ok=True)
    json.dump(body, open("logs/order_history_raw.json", "w"), indent=1)       # raw record; contains order ids, no keys
    legs = [d for d in walk(body) if "symbol" in d and "side" in d and "status" in d and ("order_id" in d or "client_order_id" in d)]
    print(f"orders returned: {len(legs)}")
    if legs:
        print("fields on one order leg:", sorted(legs[0].keys()))
    log = [json.loads(l) for l in open(f"logs/{today}-live.jsonl")]
    fills = [e for e in log if e["kind"] == "fill" and str(e.get("fill_source")).startswith("broker")]
    print(f"\nlogged broker fills: {len(fills)}")
    for leg in sorted(legs, key=lambda d: str(d.get("place_time") or d.get("create_time") or "")):
        price_keys = {k: v for k, v in leg.items() if "price" in k.lower() or "filled" in k.lower() or "qty" in k.lower() or "quantity" in k.lower()}
        print(f'{str(leg.get("symbol")):22s} {leg.get("side"):5s} {leg.get("status"):10s}', price_keys)
    print("\nlogged fills (what the engine recorded):")
    for e in fills:
        print(f'{e["time"][11:19]} {e["bot"]:10s} {e["reason_code"]:11s} {e["contract"]} qty={e["qty"]} recorded_price={e["fill_price"]}')

if __name__ == "__main__":
    main()
