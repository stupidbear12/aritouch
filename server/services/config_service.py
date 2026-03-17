import json
from datetime import datetime, timezone

import aiosqlite

from server.models import ConfigProfile


async def get_config(db: aiosqlite.Connection, bed_id: str) -> ConfigProfile | None:
    row = await db.execute("SELECT data, updated_at FROM configs WHERE bed_id = ?", (bed_id,))
    row = await row.fetchone()
    if not row:
        return None
    profile = ConfigProfile(**json.loads(row[0]))
    profile.updated_at = datetime.fromisoformat(row[1])
    return profile


async def upsert_config(db: aiosqlite.Connection, profile: ConfigProfile) -> ConfigProfile:
    now = datetime.now(timezone.utc).isoformat()
    profile.updated_at = datetime.now(timezone.utc)
    data = profile.model_dump(exclude={"updated_at"})
    await db.execute(
        "INSERT INTO configs (bed_id, data, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(bed_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
        (profile.bed_id, json.dumps(data), now),
    )
    await db.commit()
    return profile


async def get_defaults() -> dict:
    return ConfigProfile(bed_id="__default__").model_dump(exclude={"bed_id", "updated_at"})
