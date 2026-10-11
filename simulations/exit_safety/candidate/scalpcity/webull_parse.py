import re
from datetime import date, datetime
from typing import Any

from .types import ET, Bar, Quote

# Confirm these against a FILLED order's detail JSON in the phase-0 capture (plan Task 12).
FILLED_PRICE_KEYS = ("filled_price", "avg_filled_price", "average_filled_price", "avg_price")
FILLED_QTY_KEYS = ("filled_quantity", "filled_qty", "total_filled_quantity")
TERMINAL_FAILED = {"CANCELLED", "REJECTED", "FAILED", "EXPIRED"}


def _bar_rows(obj: Any) -> list[dict]:
    """Find the list of bar dicts (have 'time' and 'close') anywhere in a response."""
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and "close" in obj[0] and "time" in obj[0]:
            return obj
        for item in obj:
            found = _bar_rows(item)
            if found:
                return found
    elif isinstance(obj, dict):
        for value in obj.values():
            found = _bar_rows(value)
            if found:
                return found
    return []


def _parse_time(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(ET)


def parse_bars(response: Any, ticker: str, rth_only: bool = True) -> list[Bar]:
    rows = _bar_rows(response)
    bars = [Bar(ticker, _parse_time(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]),
                float(r["close"]), float(r.get("volume") or 0))
            for r in rows if not rth_only or r.get("trading_session", "RTH") == "RTH"]
    return sorted(bars, key=lambda b: b.ts)


def parse_snapshot(response: Any, contract: str) -> tuple[Quote, int] | None:
    """Returns (Quote, delay_minutes) or None when bid/ask are missing."""
    row = response[0] if isinstance(response, list) and response else response
    if not isinstance(row, dict) or not row.get("bid") or not row.get("ask"):
        return None
    ts = datetime.fromtimestamp(int(row["quote_time"]) / 1000, ET)
    return Quote(contract, ts, float(row["bid"]), float(row["ask"])), int(row.get("delay_minutes") or 0)


def parse_occ(contract: str) -> tuple[str, date, str, float]:
    m = re.fullmatch(r"([A-Z]+)(\d{6})([CP])(\d{8})", contract)
    if not m:
        raise ValueError(f"not an OCC symbol: {contract}")
    root, ymd, cp, strike = m.groups()
    return root, datetime.strptime(ymd, "%y%m%d").date(), "CALL" if cp == "C" else "PUT", int(strike) / 1000


def _find_key(obj: Any, keys: tuple) -> Any:
    if isinstance(obj, dict):
        for k in keys:
            if obj.get(k) not in (None, "", "0", 0):
                return obj[k]
        for v in obj.values():
            found = _find_key(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_key(v, keys)
            if found is not None:
                return found
    return None


def parse_order_detail(detail: Any) -> tuple[str, float | None, float | None]:
    """(status, filled_qty, avg_fill_price). status is the first leg's status, upper-case."""
    order = detail["orders"][0] if isinstance(detail, dict) and detail.get("orders") else detail
    status = str(order.get("status", "")).upper()
    qty = _find_key(order, FILLED_QTY_KEYS)
    price = _find_key(order, FILLED_PRICE_KEYS)
    return status, (float(qty) if qty is not None else None), (float(price) if price is not None else None)
