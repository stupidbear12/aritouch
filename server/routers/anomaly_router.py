from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from server.db.database import get_db
from server.models import AlertMessage, BehaviorEventBatch
from server.services import anomaly_service
from server.services.alert_service import manager

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("")
async def post_events(batch: BehaviorEventBatch):
    db = await get_db()
    ids = await anomaly_service.store_events(db, batch.events)

    # 이상행동 감지: 각 이벤트에 대해 규칙 평가
    detected: list = []
    for ev in batch.events:
        anomalies = await anomaly_service.detect_anomalies(db, ev)
        detected.extend(anomalies)

    # 감지된 anomaly 이벤트 저장
    anomaly_ids = []
    if detected:
        anomaly_ids = await anomaly_service.store_events(db, detected)

    # severity >= 2 이벤트를 WebSocket으로 브로드캐스트
    all_events = list(zip(batch.events, ids)) + list(zip(detected, anomaly_ids))
    for ev, eid in all_events:
        if ev.severity >= 2:
            alert = AlertMessage(
                bed_id=ev.bed_id,
                timestamp=ev.timestamp,
                alert_type=ev.event_type,
                severity=ev.severity,
                message=str(ev.data),
                event_id=eid,
            )
            await manager.broadcast(alert, ev.bed_id)

    return {"stored": len(ids), "ids": ids, "anomalies_detected": len(detected)}


@router.get("")
async def get_events(
    bed_id: Optional[str] = None,
    since: Optional[str] = None,
    severity: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
):
    db = await get_db()
    return await anomaly_service.query_events(db, bed_id, since, severity, limit, offset)


@router.get("/{event_id}")
async def get_event(event_id: int):
    db = await get_db()
    ev = await anomaly_service.get_event(db, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="event not found")
    return ev
