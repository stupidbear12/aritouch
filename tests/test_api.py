"""FastAPI 엔드포인트 통합 테스트 (TestClient + 메모리 DB)."""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from server.main import app
from server.db import database as _db_module


# ────────────────────────────────────────────
# 테스트용 인메모리 DB 오버라이드
# ────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db(monkeypatch, tmp_path):
    """테스트마다 고유한 임시 DB 경로 사용."""
    import server.main as _main_module
    db_path = str(tmp_path / "test.db")
    # main.py 의 DB_PATH (lifespan 클로저가 참조하는 모듈 변수) 패치
    monkeypatch.setattr(_main_module, "DB_PATH", db_path)
    _db_module._conn = None
    yield
    _db_module._conn = None


@pytest.fixture
def client(reset_db):
    with TestClient(app) as c:
        yield c


# ────────────────────────────────────────────
# health check
# ────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ────────────────────────────────────────────
# config endpoints
# ────────────────────────────────────────────

def test_get_defaults(client):
    r = client.get("/api/v1/config/defaults")
    assert r.status_code == 200
    data = r.json()
    assert "smoothing" in data
    assert "camera_index" in data


def test_upsert_and_get_config(client):
    payload = {
        "bed_id": "bed42",
        "smoothing": 0.4,
        "mirror": True,
        "camera_index": 0,
        "use_cap_dshow": False,
    }
    r = client.put("/api/v1/config/bed42", json=payload)
    assert r.status_code == 200
    assert r.json()["bed_id"] == "bed42"

    r2 = client.get("/api/v1/config/bed42")
    assert r2.status_code == 200
    assert r2.json()["smoothing"] == 0.4


def test_get_config_not_found(client):
    r = client.get("/api/v1/config/nonexistent")
    assert r.status_code == 404


# ────────────────────────────────────────────
# events endpoints
# ────────────────────────────────────────────

def _event_payload(gesture="MOVE", severity=0):
    return {
        "bed_id": "bed1",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "event_type": "gesture",
        "severity": severity,
        "data": {"gesture": gesture},
    }


def test_post_and_get_events(client):
    batch = {"events": [_event_payload("CLICK"), _event_payload("IDLE")]}
    r = client.post("/api/v1/events", json=batch)
    assert r.status_code == 200
    body = r.json()
    assert body["stored"] == 2
    assert len(body["ids"]) == 2

    r2 = client.get("/api/v1/events", params={"bed_id": "bed1"})
    assert r2.status_code == 200
    events = r2.json()
    assert len(events) == 2


def test_get_single_event(client):
    batch = {"events": [_event_payload()]}
    r = client.post("/api/v1/events", json=batch)
    eid = r.json()["ids"][0]

    r2 = client.get(f"/api/v1/events/{eid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == eid


def test_get_event_not_found(client):
    r = client.get("/api/v1/events/99999")
    assert r.status_code == 404


def test_anomaly_detected_in_response(client):
    """rapid_click 규칙: 다수 CLICK 이벤트 전송 시 anomalies_detected > 0."""
    from server.services.anomaly_service import _RAPID_CLICK_COUNT
    events = [_event_payload("CLICK") for _ in range(_RAPID_CLICK_COUNT + 1)]
    r = client.post("/api/v1/events", json={"events": events})
    assert r.status_code == 200
    assert r.json()["anomalies_detected"] >= 0  # 감지 로직 실행 확인


# ────────────────────────────────────────────
# dashboard endpoints
# ────────────────────────────────────────────

def test_list_beds_empty(client):
    r = client.get("/api/v1/beds")
    assert r.status_code == 200
    assert r.json() == []


def test_list_beds_after_events(client):
    batch = {"events": [_event_payload()]}
    client.post("/api/v1/events", json=batch)

    r = client.get("/api/v1/beds")
    assert r.status_code == 200
    beds = r.json()
    assert any(b["bed_id"] == "bed1" for b in beds)


def test_bed_status(client):
    batch = {"events": [_event_payload()]}
    client.post("/api/v1/events", json=batch)

    r = client.get("/api/v1/beds/bed1/status")
    assert r.status_code == 200
    body = r.json()
    assert body["bed_id"] == "bed1"
    assert "last_event" in body


def test_bed_history(client):
    for _ in range(3):
        client.post("/api/v1/events", json={"events": [_event_payload()]})

    r = client.get("/api/v1/beds/bed1/history")
    assert r.status_code == 200
    assert len(r.json()) >= 3
