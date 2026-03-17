from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class GestureConfig:
    factor: float = 1.20
    factor_min: float = 0.3
    factor_max: float = 3.0
    factor_step: float = 0.2
    z_margin: float = 5.0
    hysteresis_ratio: float = 0.95

    theta_click_in: float = 150.0
    theta_click_out: float = 165.0
    theta_drag_in: float = 150.0
    theta_drag_out: float = 165.0

    ema_len: float = 0.5
    ema_pinch: float = 0.5
    ema_cursor: float = 0.6

    dbl_hold_ms: int = 2000
    refractory_ms: int = 250

    px_per_step: float = 30.0
    deadzone_px: float = 3.0
    max_steps_per_frame: int = 6

    @classmethod
    def from_json(cls, path: str) -> GestureConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)


@dataclass
class ROIConfig:
    roi_body: bool = True
    roi_arm: bool = True
    roi_hand: bool = True
    roi_face: bool = True
    dwell_time_ms: int = 500


@dataclass
class PatientProfile:
    patient_id: str = ""
    hand_range_limit: float = 0.8
    tremor_level: int = 0
    preferred_sensitivity: float = 1.0
