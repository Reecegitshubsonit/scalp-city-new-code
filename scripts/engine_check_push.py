"""Morning check of the live paper engine, sent to the phone through ntfy.

Run by scalpcity-engine-check.timer a few minutes after the open (Mon-Fri). It reports whether the engine
answers on :8010 and how old its newest bar is. The ntfy topic comes from Watchtower's private settings file
and is never printed.
"""
import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ENGINE = "http://127.0.0.1:8010/snapshot"
NTFY_SETTINGS = Path.home() / "Documents/Codex/watchtower-private/ntfy.json"
FRESH_SEC = 180   # same limit the view uses for STALE


def service_state() -> str:
    out = subprocess.run(["systemctl", "--user", "is-active", "scalpcity-engine.service"], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def check(now: datetime) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(ENGINE, timeout=10) as response:
            snap = json.load(response)
    except Exception as error:
        return False, f"Engine not answering on :8010 ({type(error).__name__}). Service: {service_state()}."
    bots = snap.get("bots", {}).values()
    times = [datetime.fromisoformat(b["time"]) for b in bots if b.get("time")]
    pnl = sum(b.get("pnl_day") or 0 for b in bots)
    trades = sum(b.get("trades") or 0 for b in bots)
    if not times:
        return False, f"Engine up but no bars yet at {now:%H:%M} ET. Service: {service_state()}."
    newest = max(times)
    age = (now - newest).total_seconds()
    summary = f"newest bar {newest:%H:%M} ET, {trades} trades, day P&L {'-' if pnl < 0 else ''}${abs(pnl):,.2f}"
    if age > FRESH_SEC:
        return False, f"Data stale: {summary} ({int(age)}s old)."
    return True, f"Engine up, bars arriving: {summary}."


def push(ok: bool, message: str) -> None:
    keys = json.loads(NTFY_SETTINGS.read_text())
    body = {"topic": keys["alert_topic"], "title": "Scalp City: paper engine " + ("OK" if ok else "PROBLEM"),
            "message": message, "priority": 3 if ok else 5, "tags": ["chart_with_upwards_trend" if ok else "warning"]}
    request = urllib.request.Request(keys["server"].rstrip("/") + "/", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()


def main() -> int:
    ok, message = check(datetime.now(ET))
    print(message, flush=True)
    if "--dry-run" not in sys.argv:
        push(ok, message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
