from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from control.mouse_actions import MouseController
from control.zoom_actions import ZoomActions
from control.cursor_manager import CursorManager
from core.filters import EMAFilter
from gesture.candidate_scorer import GestureLabel
from gesture.config import GestureConfig, PatientProfile
from utils.constants import IDC_HAND, IDC_ARROW


@dataclass
class ApplyResult:
    label: GestureLabel = GestureLabel.IDLE
    cursor_x: int = 0
    cursor_y: int = 0
    zoom_ticks: int = 0
    hud_lines: list[str] = field(default_factory=list)


class CursorMapper:

    def __init__(
        self,
        sw: int,
        sh: int,
        ema_alpha: float = 0.6,
        profile: "PatientProfile | None" = None,
    ):
        self.sw = sw
        self.sh = sh
        self._ema_x = EMAFilter(ema_alpha)
        self._ema_y = EMAFilter(ema_alpha)
        # hand_range_limit: 커서가 이동 가능한 화면 영역 비율 (0.8 = 중앙 80%)
        limit = (profile.hand_range_limit if profile else 1.0)
        margin_x = int(sw * (1.0 - limit) / 2)
        margin_y = int(sh * (1.0 - limit) / 2)
        self._x_lo = margin_x
        self._x_hi = sw - 1 - margin_x
        self._y_lo = margin_y
        self._y_hi = sh - 1 - margin_y

    def map(self, norm_x: float, norm_y: float) -> tuple[int, int]:
        raw_x = norm_x * self.sw
        raw_y = norm_y * self.sh
        sx = self._ema_x.update(raw_x)
        sy = self._ema_y.update(raw_y)
        return int(max(self._x_lo, min(sx, self._x_hi))), int(max(self._y_lo, min(sy, self._y_hi)))


class GestureApplier:

    def __init__(
        self,
        config: GestureConfig,
        mouse: MouseController,
        zoom: ZoomActions,
        cursor: CursorManager,
        cursor_mapper: CursorMapper,
        profile: Optional[PatientProfile] = None,
    ):
        self.cfg = config
        self.mouse = mouse
        self.zoom = zoom
        self.cursor = cursor
        self.mapper = cursor_mapper
        self.profile = profile or PatientProfile()
        self._dragging = False
        self._last_apply_ms: float = 0
        self._pinch_accum: float = 0.0
        self._pinch_prev: Optional[float] = None

    def apply(self, label: GestureLabel, feature_data: dict) -> ApplyResult:
        now_ms = time.time() * 1000
        result = ApplyResult(label=label)

        anchor_x = feature_data.get("anchor_x", 0.0)
        anchor_y = feature_data.get("anchor_y", 0.0)
        cx, cy = self.mapper.map(anchor_x, anchor_y)
        result.cursor_x = cx
        result.cursor_y = cy

        if label != GestureLabel.PINCH_ZOOM:
            self.mouse.move_to(cx, cy)

        if now_ms - self._last_apply_ms < self.cfg.refractory_ms:
            if label in (GestureLabel.CLICK, GestureLabel.DOUBLE_CLICK):
                result.hud_lines.append("REFRACTORY")
                return result

        if label == GestureLabel.CLICK:
            self.mouse.click_left()
            self._last_apply_ms = now_ms
            result.hud_lines.append("CLICK")

        elif label == GestureLabel.DOUBLE_CLICK:
            self.mouse.double_click()
            self._last_apply_ms = now_ms
            result.hud_lines.append("DOUBLE_CLICK")

        elif label == GestureLabel.DRAG_START:
            if not self._dragging:
                self.mouse.drag_start()
                self._dragging = True
                self.cursor.set_active_cursor(IDC_HAND)
                result.hud_lines.append("DRAG_START")

        elif label == GestureLabel.DRAG_END:
            if self._dragging:
                self.mouse.drag_end()
                self._dragging = False
                self.cursor.restore()
                result.hud_lines.append("DRAG_END")

        elif label == GestureLabel.PINCH_ZOOM:
            pinch_d = feature_data.get("pinch_dist", 0.0)
            ticks = self._compute_zoom_ticks(pinch_d)
            if ticks != 0:
                self.mouse.move_to(cx, cy)
                self.zoom.scroll_with_ctrl(ticks)
                result.zoom_ticks = ticks
            result.hud_lines.append(f"ZOOM {ticks:+d}")

        elif label == GestureLabel.IDLE:
            if self._dragging:
                self.mouse.drag_end()
                self._dragging = False
                self.cursor.restore()
            self._pinch_prev = None
            self._pinch_accum = 0.0

        return result

    def _compute_zoom_ticks(self, pinch_d: float) -> int:
        if self._pinch_prev is None:
            self._pinch_prev = pinch_d
            return 0
        delta = pinch_d - self._pinch_prev
        self._pinch_prev = pinch_d
        if abs(delta) < self.cfg.deadzone_px:
            return 0
        self._pinch_accum += delta / self.cfg.px_per_step
        ticks = int(self._pinch_accum)
        if abs(ticks) > self.cfg.max_steps_per_frame:
            ticks = self.cfg.max_steps_per_frame * (1 if ticks > 0 else -1)
        if ticks != 0:
            self._pinch_accum -= ticks
        return ticks

    def feedback(self, result: ApplyResult):
        pass
