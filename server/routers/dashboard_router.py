import json
from typing import Optional

from fastapi import APIRouter

from server.db.database import get_db
from server.services import anomaly_service

router = APIRouter(prefix="/api/v1/beds", tags=["dashboard"])


@router.get("")
async def list_beds():
    db = await get_db()
    cur = await db.execute(
        "SELECT bed_id, MAX(timestamp) as last_seen, "
        "MAX(CASE WHEN event_type='anomaly' THEN data ELSE NULL END) as last_anomaly "
        "FROM events GROUP BY bed_id ORDER BY last_seen DESC"
    )
    rows = await cur.fetchall()
    beds = []
    for r in rows:
        beds.append({
            "bed_id": r[0],
            "last_seen": r[1],
            "last_anomaly": json.loads(r[2]) if r[2] else None,
        })
    return beds


@router.get("/{bed_id}/status")
async def bed_status(bed_id: str):
    db = await get_db()

    cur = await db.execute(
        "SELECT timestamp, event_type, severity, data FROM events "
        "WHERE bed_id = ? ORDER BY timestamp DESC LIMIT 1",
        (bed_id,),
    )
    latest = await cur.fetchone()

    cur2 = await db.execute(
        "SELECT timestamp, data FROM events "
        "WHERE bed_id = ? AND event_type = 'anomaly' ORDER BY timestamp DESC LIMIT 1",
        (bed_id,),
    )
    last_anomaly = await cur2.fetchone()

    return {
        "bed_id": bed_id,
        "last_event": {
            "timestamp": latest[0],
            "event_type": latest[1],
            "severity": latest[2],
            "data": json.loads(latest[3]),
        } if latest else None,
        "last_anomaly": {
            "timestamp": last_anomaly[0],
            "data": json.loads(last_anomaly[1]),
        } if last_anomaly else None,
    }


@router.get("/{bed_id}/history")
async def bed_history(bed_id: str, limit: int = 50, offset: int = 0):
    db = await get_db()
    return await anomaly_service.query_events(db, bed_id=bed_id, limit=limit, offset=offset)
