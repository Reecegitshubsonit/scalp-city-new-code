import json
import os
from datetime import date, datetime


class EventLog:
    """Append-only JSONL, one file per trading day and mode. The single source of truth."""

    def __init__(self, directory: str, mode: str):
        self.dir = directory
        self.mode = mode
        self._seq: dict[date, int] = {}
        self.listeners = []
        os.makedirs(directory, exist_ok=True)

    def path_for(self, day: date) -> str:
        return os.path.join(self.dir, f"{day.isoformat()}-{self.mode}.jsonl")

    def reset(self, day: date) -> None:
        """Replay only: start the day's file fresh."""
        path = self.path_for(day)
        if os.path.exists(path):
            os.remove(path)
        self._seq.pop(day, None)

    def _next_seq(self, day: date) -> int:
        if day not in self._seq:
            path = self.path_for(day)
            n = 0
            if os.path.exists(path):
                with open(path) as handle:
                    n = sum(1 for _ in handle)
            self._seq[day] = n
        self._seq[day] += 1
        return self._seq[day]

    def append(self, time: datetime, bot: str, ticker: str, kind: str, state: str = "",
               reason_code: str = "", reason_text: str = "", inputs: dict | None = None,
               charge_pct: float | None = None, **extra) -> dict:
        day = time.date()
        event = {
            "seq": self._next_seq(day), "time": time.isoformat(), "mode": self.mode,
            "bot": bot, "ticker": ticker, "kind": kind, "state": state,
            "reason_code": reason_code, "reason_text": reason_text,
            "inputs": inputs or {}, "charge_pct": charge_pct,
        }
        event.update(extra)
        with open(self.path_for(day), "a") as handle:
            handle.write(json.dumps(event, separators=(",", ":"), default=str) + "\n")
        for listener in list(self.listeners):
            listener(event)
        return event

    def read(self, day: date) -> list[dict]:
        path = self.path_for(day)
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [json.loads(line) for line in handle if line.strip()]


def build_snapshot(events: list[dict]) -> dict:
    """Current state of every bot, derived purely from the event list."""
    bots: dict[str, dict] = {}
    last_seq = 0
    for ev in events:
        last_seq = max(last_seq, ev["seq"])
        bot = ev["bot"]
        if not bot:
            continue
        row = bots.setdefault(bot, {"bot": bot, "ticker": ev["ticker"], "state": "idle", "reason_code": "",
                                    "reason_text": "", "charge_pct": None, "inputs": {}, "time": None,
                                    "pnl_day": 0.0, "trades": 0, "paused": False})
        if ev["kind"] in ("tick", "state_change"):
            row.update(state=ev["state"], reason_code=ev["reason_code"], reason_text=ev["reason_text"],
                       charge_pct=ev["charge_pct"], inputs=ev["inputs"], time=ev["time"])
        elif ev["kind"] == "trade_closed":
            row["pnl_day"] = ev.get("pnl_day", row["pnl_day"])
            row["trades"] = ev.get("trades", row["trades"])
        elif ev["kind"] == "control":
            row["paused"] = bool(ev.get("paused", row["paused"]))
    return {"bots": bots, "last_seq": last_seq}
