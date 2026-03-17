import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from server.models import BehaviorEvent


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
