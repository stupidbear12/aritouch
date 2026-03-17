from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from utils.constants import (
    IDX_MCP, IDX_PIP, IDX_DIP, IDX_TIP,
    MID_MCP, MID_PIP, MID_DIP, MID_TIP,
    THUMB_TIP,
    R_EYE_OUTER, R_EYE_INNER, L_EYE_OUTER, L_EYE_INNER,
)
from utils.geometry import angle_at, l2, normalize_landmark


@dataclass
class HandPoints:
    idx_mcp: np.ndarray
    idx_pip: np.ndarray
    idx_dip: np.ndarray
    idx_tip: np.ndarray
    mid_mcp: np.ndarray
    mid_pip: np.ndarray
    mid_dip: np.ndarray
    mid_tip: np.ndarray
    thm_tip: np.ndarray

    @property
    def cursor_anchor(self) -> np.ndarray:
        return 0.5 * (self.idx_mcp + self.mid_mcp)


def extract_eye_midpoint(face_lm, w: int, h: int) -> tuple[np.ndarray, float]:
    pts = []
    zs = []
    for idx in (R_EYE_OUTER, R_EYE_INNER, L_EYE_OUTER, L_EYE_INNER):
        xy, z = normalize_landmark(face_lm.landmark[idx], w, h)
        pts.append(xy)
        zs.append(z)
    mid_xy = np.mean(pts, axis=0).astype(np.float32)
    mid_z = float(np.mean(zs))
    return mid_xy, mid_z


def extract_hand_points(hand_lm, w: int, h: int) -> HandPoints:
    def _pt(idx):
        xy, _ = normalize_landmark(hand_lm.landmark[idx], w, h)
        return xy

    return HandPoints(
        idx_mcp=_pt(IDX_MCP), idx_pip=_pt(IDX_PIP),
        idx_dip=_pt(IDX_DIP), idx_tip=_pt(IDX_TIP),
        mid_mcp=_pt(MID_MCP), mid_pip=_pt(MID_PIP),
        mid_dip=_pt(MID_DIP), mid_tip=_pt(MID_TIP),
        thm_tip=_pt(THUMB_TIP),
    )


def compute_joint_angles(hp: HandPoints) -> dict[str, float]:
    return {
        "idx": angle_at(hp.idx_mcp, hp.idx_pip, hp.idx_dip),
        "mid": angle_at(hp.mid_mcp, hp.mid_pip, hp.mid_dip),
    }


def compute_pinch_dist(hp: HandPoints) -> float:
    return l2(hp.idx_tip, hp.thm_tip)


def compute_z_delta(eye_z: float, tip_z: float) -> float:
    return abs(eye_z - tip_z)


def build_feature_vector(
    hp: HandPoints,
    angles: dict[str, float],
    pinch: float,
    z_delta: float,
) -> np.ndarray:
    return np.array([
        angles.get("idx", 0.0),
        angles.get("mid", 0.0),
        pinch,
        z_delta,
        hp.cursor_anchor[0],
        hp.cursor_anchor[1],
    ], dtype=np.float32)
