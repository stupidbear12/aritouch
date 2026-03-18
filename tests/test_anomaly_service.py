"""이상행동 감지 규칙 단위 테스트 (aiosqlite 메모리 DB 사용)."""
import asyncio
import json
from datetime import datetime, timezone, timedelta

import pytest
import aiosqlite

from server.models import BehaviorEvent
from server.services.anomaly_service import (
    detect_anomalies,
    check_idle_timeout,
    store_events,
    _RAPID_CLICK_COUNT,
    _RAPID_CLICK_WINDOW_SEC,
    _IDLE_TIMEOUT_SEC,
    _ABNORMAL_Z_THRESHOLD,
)

# ────────────────────────────────────────────
# DB 픽스처
# ────────────────────────────────────────────

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(
            "CREATE TABLE events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "bed_id TEXT NOT NULL, "
            "timestamp TEXT, "
            "event_type TEXT, "
            "severity INTEGER DEFAULT 0, "
            "data TEXT)"
        )
        await conn.commit()
        yield conn


def _make_click_event(bed_id="bed1", offset_sec=0.0):
    ts = datetime.now(tz=timezone.utc) + timedelta(seconds=offset_sec)
    return BehaviorEvent(
        bed_id=bed_id,
        timestamp=ts,
        event_type="gesture",
        severity=0,
        data={"gesture": "CLICK"},
    )


def _make_event(event_type="status", data=None, severity=0):
    return BehaviorEvent(
        bed_id="bed1",
        timestamp=datetime.now(tz=timezone.utc),
        event_type=event_type,
        severity=severity,
        data=data or {},
    )


# ────────────────────────────────────────────
# store_events
# ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_store_events_returns_ids(db):
    events = [_make_click_event(), _make_click_event()]
    ids = await store_events(db, events)
    assert len(ids) == 2
    assert all(isinstance(i, int) for i in ids)


# ────────────────────────────────────────────
# detect_anomalies: rapid_click
# ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_anomaly_below_threshold(db):
    """클릭 횟수가 임계값 미만이면 anomaly 없음."""
    events = [_make_click_event() for _ in range(_RAPID_CLICK_COUNT - 1)]
    await store_events(db, events)
    anomalies = await detect_anomalies(db, _make_click_event())
    rapid = [a for a in anomalies if a.data.get("rule") == "rapid_click"]
    assert len(rapid) == 0


@pytest.mark.asyncio
async def test_rapid_click_detected(db):
    """빠른 시간 내 클릭 N회 이상 → rapid_click anomaly."""
    events = [_make_click_event() for _ in range(_RAPID_CLICK_COUNT)]
    await store_events(db, events)
    anomalies = await detect_anomalies(db, _make_click_event())
    rapid = [a for a in anomalies if a.data.get("rule") == "rapid_click"]
    assert len(rapid) == 1
    assert rapid[0].severity == 2


# ────────────────────────────────────────────
# detect_anomalies: abnormal_depth
# ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_anomaly_normal_z(db):
    ev = _make_event(data={"z_delta": _ABNORMAL_Z_THRESHOLD - 1.0})
    anomalies = await detect_anomalies(db, ev)
    depth = [a for a in anomalies if a.data.get("rule") == "abnormal_depth"]
    assert len(depth) == 0


@pytest.mark.asyncio
async def test_abnormal_depth_detected(db):
    ev = _make_event(data={"z_delta": _ABNORMAL_Z_THRESHOLD + 10.0})
    anomalies = await detect_anomalies(db, ev)
    depth = [a for a in anomalies if a.data.get("rule") == "abnormal_depth"]
    assert len(depth) == 1
    assert depth[0].severity == 2


# ────────────────────────────────────────────
# check_idle_timeout
# ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_timeout_when_recent(db):
    ev = _make_event()
    await store_events(db, [ev])
    now = datetime.now(tz=timezone.utc)
    result = await check_idle_timeout(db, "bed1", now)
    assert result is None


@pytest.mark.asyncio
async def test_idle_timeout_detected(db):
    old_ts = datetime.now(tz=timezone.utc) - timedelta(seconds=_IDLE_TIMEOUT_SEC + 10)
    ev = BehaviorEvent(
        bed_id="bed1",
        timestamp=old_ts,
        event_type="status",
        severity=0,
        data={},
    )
    await store_events(db, [ev])
    now = datetime.now(tz=timezone.utc)
    result = await check_idle_timeout(db, "bed1", now)
    assert result is not None
    assert result.data["rule"] == "idle_timeout"
    assert result.severity == 1


@pytest.mark.asyncio
async def test_idle_timeout_no_events(db):
    """이벤트가 없으면 None 반환."""
    now = datetime.now(tz=timezone.utc)
    result = await check_idle_timeout(db, "unknown_bed", now)
    assert result is None
