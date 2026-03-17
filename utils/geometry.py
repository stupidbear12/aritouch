from __future__ import annotations

import math
from typing import Optional

import numpy as np


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def ema(prev: Optional[float], val: float, alpha: float) -> float:
    if prev is None:
        return val
    return alpha * val + (1.0 - alpha) * prev


def l2(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def angle_at(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc))
    if denom == 0:
        return 0.0
    cos_theta = float(np.clip(np.dot(ba, bc) / denom, -1.0, 1.0))
    return math.degrees(math.acos(cos_theta))


def normalize_landmark(lm_item, w: int, h: int) -> tuple[np.ndarray, float]:
    xy = np.array([lm_item.x * w, lm_item.y * h], dtype=np.float32)
    z = float(lm_item.z) * w
    return xy, z
