from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.services.alert_service import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket, bed_id: Optional[str] = None):
    await manager.connect(ws, bed_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws, bed_id)
