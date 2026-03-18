"""gesture 파이프라인 단위 테스트 (MediaPipe 없이 실행 가능)."""
import numpy as np
import pytest

from gesture.config import GestureConfig, PatientProfile
from gesture.candidate_scorer import GestureLabel, RuleBasedScorer
from gesture.gesture_decider import GestureDecider
from gesture.context_fusion import ContextFusion, ContextInfo
from utils.geometry import angle_at, l2, clamp


# ────────────────────────────────────────────
# geometry utilities
# ────────────────────────────────────────────

def test_clamp():
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-1.0, 0.0, 10.0) == 0.0
    assert clamp(11.0, 0.0, 10.0) == 10.0


def test_l2():
    a = np.array([0.0, 0.0])
    b = np.array([3.0, 4.0])
    assert abs(l2(a, b) - 5.0) < 1e-6


def test_angle_at_straight():
    # 세 점이 일직선이면 180도
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 0.0])
    c = np.array([2.0, 0.0])
    assert abs(angle_at(a, b, c) - 180.0) < 1e-4


def test_angle_at_right():
    # 직각이면 90도
    a = np.array([0.0, 1.0])
    b = np.array([0.0, 0.0])
    c = np.array([1.0, 0.0])
    assert abs(angle_at(a, b, c) - 90.0) < 1e-4


# ────────────────────────────────────────────
# RuleBasedScorer
# ────────────────────────────────────────────

@pytest.fixture
def scorer():
    return RuleBasedScorer(GestureConfig())


def test_scorer_idle_when_extended(scorer):
    """손가락이 완전히 펴있으면 IDLE이 가장 높아야 함."""
    scores = scorer.score({"idx": 180.0, "mid": 180.0}, pinch_dist=80.0, z_active=False)
    assert scores[GestureLabel.IDLE] > 0.9
    assert scores[GestureLabel.CLICK] == 0.0


def test_scorer_click_when_bent(scorer):
    """검지가 많이 구부러지면 CLICK 점수가 높아야 함."""
    scores = scorer.score({"idx": 100.0, "mid": 180.0}, pinch_dist=80.0, z_active=False)
    assert scores[GestureLabel.CLICK] > 0.8


def test_scorer_drag_when_middle_bent(scorer):
    """중지가 구부러지면 DRAG_START 점수가 높아야 함."""
    scores = scorer.score({"idx": 180.0, "mid": 100.0}, pinch_dist=80.0, z_active=False)
    assert scores[GestureLabel.DRAG_START] > 0.8


def test_scorer_pinch_requires_z_active(scorer):
    """z_active=False이면 pinch 점수 0."""
    scores = scorer.score({"idx": 180.0, "mid": 180.0}, pinch_dist=5.0, z_active=False)
    assert scores[GestureLabel.PINCH_ZOOM] == 0.0


def test_scorer_pinch_when_z_active(scorer):
    """z_active=True이고 거리가 가까우면 PINCH 점수 높음."""
    scores = scorer.score({"idx": 180.0, "mid": 180.0}, pinch_dist=5.0, z_active=True)
    assert scores[GestureLabel.PINCH_ZOOM] > 0.8


def test_scorer_sensitivity_scaling():
    """preferred_sensitivity가 높을수록 더 쉽게 클릭 발동."""
    profile_low  = PatientProfile(preferred_sensitivity=0.5)
    profile_high = PatientProfile(preferred_sensitivity=2.0)
    scorer_low  = RuleBasedScorer(GestureConfig(), profile=profile_low)
    scorer_high = RuleBasedScorer(GestureConfig(), profile=profile_high)
    angles = {"idx": 145.0, "mid": 180.0}
    low_score  = scorer_low.score(angles, 80.0, False)[GestureLabel.CLICK]
    high_score = scorer_high.score(angles, 80.0, False)[GestureLabel.CLICK]
    assert high_score >= low_score


# ────────────────────────────────────────────
# GestureDecider
# ────────────────────────────────────────────

def _click_scores():
    return {
        GestureLabel.CLICK: 0.9,
        GestureLabel.IDLE: 0.1,
        GestureLabel.DRAG_START: 0.0,
        GestureLabel.PINCH_ZOOM: 0.0,
        GestureLabel.MOVE: 0.0,
        GestureLabel.DOUBLE_CLICK: 0.0,
        GestureLabel.DRAG_END: 0.0,
    }


def test_decider_requires_stable_frames():
    """min_stable_frames=3이면 3회 연속 후 결정 반환."""
    decider = GestureDecider(min_stable_frames=3)
    assert decider.update(_click_scores()) is None
    assert decider.update(_click_scores()) is None
    result = decider.update(_click_scores())
    assert result == GestureLabel.CLICK


def test_decider_reset_on_low_confidence():
    """낮은 confidence 이면 streak 초기화."""
    decider = GestureDecider(min_stable_frames=2, min_confidence=0.5)
    decider.update(_click_scores())  # streak=1
    low = {k: 0.1 for k in GestureLabel}
    decider.update(low)              # streak 초기화
    result = decider.update(_click_scores())  # streak=1, 아직 부족
    assert result is None


def test_decider_tremor_level():
    """tremor_level=2이면 자동으로 min_stable_frames 증가."""
    profile = PatientProfile(tremor_level=2)
    decider = GestureDecider(profile=profile)
    assert decider.min_stable_frames >= 4


def test_decider_reset():
    decider = GestureDecider(min_stable_frames=2)
    decider.update(_click_scores())
    decider.reset()
    assert decider._streak == 0
    assert decider._prev is None


# ────────────────────────────────────────────
# ContextFusion
# ────────────────────────────────────────────

def test_fusion_none_becomes_idle():
    fusion = ContextFusion()
    result = fusion.fuse(None, ContextInfo())
    assert result == GestureLabel.IDLE


def test_fusion_passes_allowed():
    fusion = ContextFusion()
    ctx = ContextInfo(allowed_commands={GestureLabel.CLICK, GestureLabel.IDLE})
    assert fusion.fuse(GestureLabel.CLICK, ctx) == GestureLabel.CLICK


def test_fusion_blocks_disallowed():
    fusion = ContextFusion()
    ctx = ContextInfo(allowed_commands={GestureLabel.IDLE})
    assert fusion.fuse(GestureLabel.CLICK, ctx) == GestureLabel.IDLE


def test_fusion_empty_allowed_passes_all():
    """allowed_commands가 비어있으면 모든 제스처 허용."""
    fusion = ContextFusion()
    ctx = ContextInfo(allowed_commands=set())
    assert fusion.fuse(GestureLabel.DRAG_START, ctx) == GestureLabel.DRAG_START
