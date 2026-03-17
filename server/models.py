from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ConfigProfile(BaseModel):
    bed_id: str
    smoothing: float = 0.3
    mirror: bool = False
    camera_index: int = 0
    use_cap_dshow: bool = True
    tmin_ms: int = 120
    vmax_px: int = 35
    k_in: float = 2.0
    k_out: float = 1.0
    margin: float = 0.005
    alpha_base: float = 0.02
    alpha_sigma: float = 0.02
    click_on_touch: bool = False
    touch_polarity: str = "auto"
    zoom_gain: float = 1.6
    wheel_step: int = 120
    pinch_deadzone: float = 0.004
    zoom_center_follow_cursor: bool = True
    updated_at: Optional[datetime] = None


class BehaviorEvent(BaseModel):
    bed_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: Literal["gesture", "anomaly", "status"] = "status"
    severity: int = Field(default=0, ge=0, le=3)
    data: dict[str, Any] = Field(default_factory=dict)


class BehaviorEventBatch(BaseModel):
    events: list[BehaviorEvent]


class BedStatus(BaseModel):
    bed_id: str
    patient_present: bool = False
    last_gesture: str = ""
    last_anomaly: Optional[str] = None
    uptime_seconds: int = 0
    last_seen: Optional[datetime] = None


class AlertMessage(BaseModel):
    bed_id: str
    timestamp: datetime
    alert_type: str
    severity: int
    message: str
    event_id: Optional[int] = None
