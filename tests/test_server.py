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


def test_history_endpoint_returns_bars_and_404s(tmp_path):
    from scalpcity.history import BarStore
    from scalpcity.types import Bar
    log = EventLog(str(tmp_path), "live")
    store = BarStore()
    store.add(Bar("QQQ", t(9, 30), 100, 101, 99, 100.5, 10))
    log.append(t(9, 30), "QQQ-VWAP", "QQQ", "tick", state="idle", inputs={"price": 100.5, "vwap": 100.0, "ema9": 1, "ema21": 2, "ema50": 3})
    app = create_app(log, lambda: DAY, lambda *a: None, BOTS, web_dir=str(tmp_path / "nonexistent"), history_fn=store.get)
    with TestClient(app) as client:
        h = client.get("/history", params={"ticker": "QQQ"}).json()
        assert h["bars"][0]["close"] == 100.5 and h["levels"][0]["vwap"] == 100.0
        assert client.get("/history", params={"ticker": "ZZZ"}).status_code == 404
    bare = create_app(log, lambda: DAY, lambda *a: None, BOTS, web_dir=str(tmp_path / "nonexistent"))
    with TestClient(bare) as client:
        assert client.get("/history", params={"ticker": "QQQ"}).status_code == 404


def test_days_and_day_endpoints(tmp_path):
    log = EventLog(str(tmp_path), "replay")
    log.append(t(9, 31), "QQQ-VWAP", "QQQ", "tick", state="idle")
    app = create_app(log, lambda: DAY, lambda *a: None, BOTS, web_dir=str(tmp_path / "nonexistent"))
    with TestClient(app) as client:
        days = client.get("/days").json()["days"]
        assert days[0]["day"] == "2026-10-08" and days[0]["mode"] == "replay" and days[0]["events"] == 1
        got = client.get("/day", params={"day": "2026-10-08", "mode": "replay"}).json()
        assert got["events"][0]["bot"] == "QQQ-VWAP"
        assert client.get("/day", params={"day": "2026-10-01"}).status_code == 404
        assert client.get("/day", params={"day": "../x"}).status_code == 400
        assert client.get("/day", params={"day": "2026-10-08", "mode": "x"}).status_code == 400


def test_trades_endpoint(tmp_path):
    log = EventLog(str(tmp_path), "live")
    log.append(t(9, 50), "QQQ-VWAP", "QQQ", "trade_closed", state="cooldown", pnl=55.0, pnl_day=55.0, trades=1)
    app = create_app(log, lambda: DAY, lambda *a: None, BOTS, web_dir=str(tmp_path / "nonexistent"))
    with TestClient(app) as client:
        got = client.get("/trades", params={"day": "2026-10-08"}).json()
        assert got["trades"][0]["pnl"] == 55.0 and got["trades"][0]["bot"] == "QQQ-VWAP"
        assert client.get("/trades", params={"day": "2026-10-01"}).json()["trades"] == []
        assert client.get("/trades", params={"day": "../x"}).status_code == 400


def test_history_with_day_serves_webull_bars_and_that_days_markers(tmp_path):
    import json
    webull = tmp_path / "webull"; (webull / "2026-10-07").mkdir(parents=True)
    (webull / "2026-10-07" / "stock-QQQ.json").write_text(json.dumps([
        {"time": "2026-10-07T13:30:00.000+0000", "open": "753.8", "close": "754.03", "high": "754.37", "low": "753.35", "volume": "5"}]))
    log = EventLog(str(tmp_path / "logs"), "live")
    app = create_app(log, lambda: DAY, lambda *a: None, BOTS, web_dir=str(tmp_path / "nonexistent"), webull_dir=str(webull))
    c = TestClient(app)
    r = c.get("/history", params={"ticker": "QQQ", "day": "2026-10-07"})
    assert r.status_code == 200 and r.json()["bars"][0]["close"] == 754.03
    assert r.json()["bars"][0]["time"] == "2026-10-07T09:30:00-04:00"
    assert c.get("/history", params={"ticker": "QQQ", "day": "2026-10-08"}).status_code == 404   # no Webull bars that day
    assert c.get("/history", params={"ticker": "QQQ", "day": "bad"}).status_code == 400
    assert c.get("/history", params={"ticker": "ZZZ", "day": "2026-10-07"}).status_code == 404
