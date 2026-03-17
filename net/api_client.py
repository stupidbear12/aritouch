from __future__ import annotations

from typing import Any, Optional

import httpx


class AirTouchClient:

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 3.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def fetch_config(self, bed_id: str) -> dict | None:
        try:
            r = httpx.get(f"{self._base}/api/v1/config/{bed_id}", timeout=self._timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def post_events(self, events: list[dict]) -> dict | None:
        try:
            r = httpx.post(
                f"{self._base}/api/v1/events",
                json={"events": events},
                timeout=self._timeout,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def update_status(self, bed_id: str, data: dict) -> dict | None:
        event = {
            "bed_id": bed_id,
            "event_type": "status",
            "severity": 0,
            "data": data,
        }
        return self.post_events([event])

    def push_config(self, bed_id: str, config: dict) -> dict | None:
        try:
            r = httpx.put(
                f"{self._base}/api/v1/config/{bed_id}",
                json={**config, "bed_id": bed_id},
                timeout=self._timeout,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None
