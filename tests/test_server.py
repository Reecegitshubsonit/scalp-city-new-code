from datetime import date, datetime

from fastapi.testclient import TestClient

from scalpcity.events import EventLog
from scalpcity.server import create_app
from scalpcity.types import ET

DAY = date(2026, 10, 8)
BOTS = ["QQQ-VWAP", "QQQ-EMA50"]


def t(h, m):
    return datetime(2026, 10, 8, h, m, tzinfo=ET)


def make(tmp_path):
    log = EventLog(str(tmp_path), "live")
    calls = []
    app = create_app(log, lambda: DAY, lambda bot, paused, when: calls.append((bot, paused)), BOTS, web_dir=str(tmp_path / "nonexistent"))
    return log, calls, app


def test_snapshot_lists_every_bot_even_before_events(tmp_path):
    log, _, app = make(tmp_path)
    with TestClient(app) as client:
        snap = client.get("/snapshot").json()
        assert set(snap["bots"]) == set(BOTS) and snap["bots"]["QQQ-VWAP"]["reason_code"] == "NO_DATA"
        log.append(t(9, 31), "QQQ-VWAP", "QQQ", "tick", state="forming", reason_code="WATCHING", charge_pct=55.0)
        assert client.get("/snapshot").json()["bots"]["QQQ-VWAP"]["state"] == "forming"


def test_websocket_sends_snapshot_then_streams_new_events(tmp_path):
    log, _, app = make(tmp_path)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            first = ws.receive_json()
            assert first["type"] == "snapshot" and "QQQ-VWAP" in first["bots"]
            log.append(t(9, 32), "QQQ-VWAP", "QQQ", "state_change", state="fired", reason_code="SIGNAL")
            msg = ws.receive_json()
            assert msg["type"] == "event" and msg["event"]["state"] == "fired"


def test_pause_endpoint_calls_back_and_rejects_unknown_bot(tmp_path):
    _, calls, app = make(tmp_path)
    with TestClient(app) as client:
        assert client.post("/control/pause", json={"bot": "QQQ-VWAP", "paused": True}).json()["ok"] is True
        assert calls == [("QQQ-VWAP", True)]
        assert client.post("/control/pause", json={"bot": "NOPE", "paused": True}).status_code == 404
