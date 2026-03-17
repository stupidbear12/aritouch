from __future__ import annotations

from typing import Optional

from gesture.candidate_scorer import GestureLabel


class GestureDecider:

    def __init__(self, min_stable_frames: int = 2, min_confidence: float = 0.3):
        self.min_stable_frames = min_stable_frames
        self.min_confidence = min_confidence
        self._prev: Optional[GestureLabel] = None
        self._streak: int = 0

    def update(self, scores: dict[GestureLabel, float]) -> GestureLabel | None:
        best = max(scores, key=scores.get)
        if scores[best] < self.min_confidence:
            self._streak = 0
            return None
        if best == self._prev:
            self._streak += 1
        else:
            self._streak = 1
            self._prev = best
        if self._streak >= self.min_stable_frames:
            return best
        return None

    def reset(self):
        self._prev = None
        self._streak = 0
