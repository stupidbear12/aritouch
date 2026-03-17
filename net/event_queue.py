from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from net.api_client import AirTouchClient


class EventQueue:

    def __init__(
        self,
        client: AirTouchClient,
        flush_interval: float = 5.0,
        max_buffer: int = 500,
    ):
        self._client = client
        self._flush_interval = flush_interval
        self._max_buffer = max_buffer
        self._buffer: deque[dict] = deque(maxlen=max_buffer)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def put(self, event: dict):
        with self._lock:
            self._buffer.append(event)

    def _flush(self):
        with self._lock:
            if not self._buffer:
                return
            batch = list(self._buffer)
            self._buffer.clear()
        self._client.post_events(batch)

    def _run(self):
        while not self._stop.is_set():
            self._stop.wait(self._flush_interval)
            self._flush()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        self._flush()
