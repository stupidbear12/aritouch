from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import WebSocket

from server.models import AlertMessage


class ConnectionManager:

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}
        self._all: list[WebSocket] = []

    async def connect(self, ws: WebSocket, bed_id: str | None = None):
        await ws.accept()
        self._all.append(ws)
        if bed_id:
            self._connections.setdefault(bed_id, []).append(ws)

    def disconnect(self, ws: WebSocket, bed_id: str | None = None):
        if ws in self._all:
            self._all.remove(ws)
        if bed_id and bed_id in self._connections:
            conns = self._connections[bed_id]
            if ws in conns:
                conns.remove(ws)

    async def broadcast(self, alert: AlertMessage, bed_id: str | None = None):
        payload = alert.model_dump_json()
        targets = self._connections.get(bed_id, []) if bed_id else self._all
        dead = []
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, bed_id)


manager = ConnectionManager()
