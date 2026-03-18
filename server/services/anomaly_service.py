import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from server.models import BehaviorEvent

# 이상행동 감지 임계값
_RAPID_CLICK_WINDOW_SEC = 0.5   # 이 시간 내
_RAPID_CLICK_COUNT      = 5     # CLICK이 N회 이상 → rapid_click
_IDLE_TIMEOUT_SEC       = 300   # 마지막 이벤트로부터 N초 이상 무동작 → idle_timeout
_ABNORMAL_Z_THRESHOLD   = 80.0  # z_delta 이 값 초과 시 비정상


async def detect_anomalies(
    db: aiosqlite.Connection,
    event: BehaviorEvent,
) -> list[BehaviorEvent]:
    """이벤트 하나를 받아 이상행동 감지 후 anomaly 이벤트 목록 반환."""
    anomalies: list[BehaviorEvent] = []

    # 규칙 1: 급속 클릭 (rapid_click)
    if event.event_type == "gesture" and event.data.get("gesture") == "CLICK":
        since = (event.timestamp.timestamp() - _RAPID_CLICK_WINDOW_SEC)
        since_iso = datetime.fromtimestamp(since, tz=timezone.utc).isoformat()
        cur = await db.execute(
            "SELECT COUNT(*) FROM events "
            "WHERE bed_id=? AND event_type='gesture' AND data LIKE '%\"gesture\": \"CLICK\"%' "
            "AND timestamp >= ?",
            (event.bed_id, since_iso),
        )
        row = await cur.fetchone()
        if row and row[0] >= _RAPID_CLICK_COUNT:
            anomalies.append(BehaviorEvent(
                bed_id=event.bed_id,
                timestamp=event.timestamp,
                event_type="anomaly",
                severity=2,
                data={"rule": "rapid_click", "count": row[0], "window_sec": _RAPID_CLICK_WINDOW_SEC},
            ))

    # 규칙 2: 비정상 Z-depth (abnormal_depth)
    if event.event_type in ("gesture", "status"):
        z_delta = event.data.get("z_delta", 0.0)
        if isinstance(z_delta, (int, float)) and z_delta > _ABNORMAL_Z_THRESHOLD:
            anomalies.append(BehaviorEvent(
                bed_id=event.bed_id,
                timestamp=event.timestamp,
                event_type="anomaly",
                severity=2,
                data={"rule": "abnormal_depth", "z_delta": z_delta, "threshold": _ABNORMAL_Z_THRESHOLD},
            ))

    return anomalies


async def check_idle_timeout(
    db: aiosqlite.Connection,
    bed_id: str,
    now: datetime,
) -> Optional[BehaviorEvent]:
    """마지막 이벤트 이후 idle_timeout 초 이상 지났으면 anomaly 반환."""
    cur = await db.execute(
        "SELECT timestamp FROM events WHERE bed_id=? ORDER BY timestamp DESC LIMIT 1",
        (bed_id,),
    )
    row = await cur.fetchone()
    if not row:
        return None
    try:
        last_ts = datetime.fromisoformat(row[0])
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        elapsed = (now - last_ts).total_seconds()
        if elapsed >= _IDLE_TIMEOUT_SEC:
            return BehaviorEvent(
                bed_id=bed_id,
                timestamp=now,
                event_type="anomaly",
                severity=1,
                data={"rule": "idle_timeout", "elapsed_sec": round(elapsed, 1)},
            )
    except (ValueError, TypeError):
        pass
    return None


async def store_events(db: aiosqlite.Connection, events: list[BehaviorEvent]) -> list[int]:
    ids = []
    for ev in events:
        cur = await db.execute(
            "INSERT INTO events (bed_id, timestamp, event_type, severity, data) VALUES (?, ?, ?, ?, ?)",
            (
                ev.bed_id,
                ev.timestamp.isoformat(),
                ev.event_type,
                ev.severity,
                json.dumps(ev.data),
            ),
        )
        ids.append(cur.lastrowid)
    await db.commit()
    return ids


async def query_events(
    db: aiosqlite.Connection,
    bed_id: Optional[str] = None,
    since: Optional[str] = None,
    severity: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    clauses = []
    params = []
    if bed_id:
        clauses.append("bed_id = ?")
        params.append(bed_id)
    if since:
        clauses.append("timestamp >= ?")
        params.append(since)
    if severity is not None:
        clauses.append("severity >= ?")
        params.append(severity)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM events{where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    cur = await db.execute(sql, params)
    rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "bed_id": r[1],
            "timestamp": r[2],
            "event_type": r[3],
            "severity": r[4],
            "data": json.loads(r[5]),
        }
        for r in rows
    ]


async def get_event(db: aiosqlite.Connection, event_id: int) -> dict | None:
    cur = await db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    r = await cur.fetchone()
    if not r:
        return None
    return {
        "id": r[0],
        "bed_id": r[1],
        "timestamp": r[2],
        "event_type": r[3],
        "severity": r[4],
        "data": json.loads(r[5]),
    }
