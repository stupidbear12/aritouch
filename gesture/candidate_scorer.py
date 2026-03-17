from __future__ import annotations

from enum import Enum, auto

from gesture.config import GestureConfig
from utils.geometry import clamp


class GestureLabel(Enum):
    IDLE = auto()
    MOVE = auto()
    CLICK = auto()
    DOUBLE_CLICK = auto()
    DRAG_START = auto()
    DRAG_END = auto()
    PINCH_ZOOM = auto()


class RuleBasedScorer:

    def __init__(self, config: GestureConfig):
        self.cfg = config

    def score(
        self,
        angles: dict[str, float],
        pinch_dist: float,
        z_active: bool,
    ) -> dict[GestureLabel, float]:
        idx_angle = angles.get("idx", 180.0)
        mid_angle = angles.get("mid", 180.0)

        click_score = clamp((self.cfg.theta_click_in - idx_angle) / 15.0, 0.0, 1.0)
        drag_score = clamp((self.cfg.theta_drag_in - mid_angle) / 15.0, 0.0, 1.0)
        pinch_score = clamp(1.0 - pinch_dist / 50.0, 0.0, 1.0) if z_active else 0.0

        idle_score = clamp(1.0 - max(click_score, drag_score, pinch_score), 0.0, 1.0)

        return {
            GestureLabel.CLICK: click_score,
            GestureLabel.DRAG_START: drag_score,
            GestureLabel.PINCH_ZOOM: pinch_score,
            GestureLabel.IDLE: idle_score,
            GestureLabel.MOVE: 0.0,
            GestureLabel.DOUBLE_CLICK: 0.0,
            GestureLabel.DRAG_END: 0.0,
        }
