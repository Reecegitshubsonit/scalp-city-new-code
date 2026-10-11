import asyncio
import pathlib
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Callable

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .events import EventLog, build_snapshot
import re

from .history import build_history, build_trades, list_days, read_cached_bars, read_day
from .types import ET


class Hub:
    """Fans events out to websocket clients. push() may be called from any thread."""

    def __init__(self):
        self.clients: set[asyncio.Queue] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def push(self, event: dict) -> None:
        if self.loop is None:
            return
        for q in list(self.clients):
            self.loop.call_soon_threadsafe(q.put_nowait, event)


class PauseBody(BaseModel):
    bot: str
    paused: bool


def create_app(log: EventLog, day_fn: Callable, set_paused: Callable[[str, bool, datetime], None],
               bot_ids: list[str], web_dir: str | None = None, history_fn: Callable[[str], list] | None = None, cache_dir: str | None = None) -> FastAPI:
    hub = Hub()

    @asynccontextmanager
    async def lifespan(_app):
        hub.loop = asyncio.get_running_loop()
        yield

    app = FastAPI(title="Scalp City", lifespan=lifespan)
    log.listeners.append(hub.push)

    @app.get("/snapshot")
    def snapshot():
        snap = build_snapshot(log.read(day_fn()))
        for bot in bot_ids:
            snap["bots"].setdefault(bot, {"bot": bot, "ticker": bot.split("-")[0], "state": "idle", "reason_code": "NO_DATA",
                                          "reason_text": "no events yet", "charge_pct": None, "inputs": {}, "time": None,
                                          "pnl_day": 0.0, "trades": 0, "paused": False})
        return snap

    @app.get("/history")
    def history(ticker: str, day: str | None = None, mode: str | None = None):
        if ticker not in {b.split("-")[0] for b in bot_ids}:
            raise HTTPException(404, "unknown ticker or no history")
        if day is None:
            if history_fn is None:
                raise HTTPException(404, "unknown ticker or no history")
            return build_history(ticker, history_fn(ticker), log.read(day_fn()))
        # a past day: real cached candles, with levels and markers from that day's event log
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) or mode not in (None, "live", "replay"):
            raise HTTPException(400, "bad day or mode")
        bars = read_cached_bars(cache_dir, ticker, day) if cache_dir else None
        if not bars:
            raise HTTPException(404, "no cached bars for that day")
        events: list[dict] = []
        for m in ((mode,) if mode else ("live", "replay")):
            events = read_day(log.dir, day, m) or []
            if events:
                break
        return build_history(ticker, bars, events)

    @app.get("/days")
    def days():
        return {"days": list_days(log.dir)}

    @app.get("/day")
    def day(day: str, mode: str = "replay"):
        events = read_day(log.dir, day, mode)
        if events is None:
            raise HTTPException(400, "bad day or mode")
        if not events:
            raise HTTPException(404, "no log for that day")
        return {"day": day, "mode": mode, "events": events}

    @app.get("/trades")
    def trades(day: str, mode: str = "live"):
        events = read_day(log.dir, day, mode)
        if events is None:
            raise HTTPException(400, "bad day or mode")
        return {"day": day, "mode": mode, "trades": build_trades(events)}

    @app.post("/control/pause")
    def pause(body: PauseBody):
        if body.bot not in bot_ids:
            raise HTTPException(404, "unknown bot")
        set_paused(body.bot, body.paused, datetime.now(ET))
        return {"ok": True, "bot": body.bot, "paused": body.paused}

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        queue: asyncio.Queue = asyncio.Queue()
        hub.clients.add(queue)
        try:
            await socket.send_json({"type": "snapshot", **snapshot()})
            while True:
                await socket.send_json({"type": "event", "event": await queue.get()})
        except WebSocketDisconnect:
            pass
        finally:
            hub.clients.discard(queue)

    directory = web_dir or str(pathlib.Path(__file__).resolve().parent.parent / "web")
    if pathlib.Path(directory).exists():
        app.mount("/", StaticFiles(directory=directory, html=True), name="web")
    return app
