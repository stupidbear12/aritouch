import aiosqlite

_db_path: str = "airtouch.db"
_conn: aiosqlite.Connection | None = None


async def init_db(db_path: str = "airtouch.db"):
    global _db_path, _conn
    _db_path = db_path
    _conn = await aiosqlite.connect(_db_path)
    _conn.row_factory = aiosqlite.Row
    await _conn.executescript("""
        CREATE TABLE IF NOT EXISTS configs (
            bed_id     TEXT PRIMARY KEY,
            data       TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            bed_id     TEXT NOT NULL,
            timestamp  TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity   INTEGER NOT NULL DEFAULT 0,
            data       TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_bed ON events(bed_id, timestamp);
    """)
    await _conn.commit()


async def get_db() -> aiosqlite.Connection:
    if _conn is None:
        await init_db(_db_path)
    return _conn


async def close_db():
    global _conn
    if _conn:
        await _conn.close()
        _conn = None
