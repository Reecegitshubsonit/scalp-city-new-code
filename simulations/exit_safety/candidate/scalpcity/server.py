import asyncio
import pathlib
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Callable

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .events import EventLog, build_snapshot
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
               bot_ids: list[str], web_dir: str | None = None) -> FastAPI:
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
