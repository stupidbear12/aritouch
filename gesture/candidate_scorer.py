from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from gesture.config import GestureConfig, PatientProfile
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

    def __init__(self, config: GestureConfig, profile: Optional[PatientProfile] = None):
        self.cfg = config
        self.profile = profile or PatientProfile()

    def score(
        self,
        angles: dict[str, float],
        pinch_dist: float,
        z_active: bool,
    ) -> dict[GestureLabel, float]:
        idx_angle = angles.get("idx", 180.0)
        mid_angle = angles.get("mid", 180.0)

        # preferred_sensitivity로 threshold 스케일링: 감도가 높을수록 더 쉽게 발동
        sens = clamp(self.profile.preferred_sensitivity, 0.1, 3.0)
        effective_click_in = self.cfg.theta_click_in * (1.0 + 0.1 * (sens - 1.0))
        effective_drag_in  = self.cfg.theta_drag_in  * (1.0 + 0.1 * (sens - 1.0))

        click_score = clamp((effective_click_in - idx_angle) / 15.0, 0.0, 1.0)
        drag_score  = clamp((effective_drag_in  - mid_angle) / 15.0, 0.0, 1.0)
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
