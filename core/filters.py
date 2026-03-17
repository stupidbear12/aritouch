from __future__ import annotations

from typing import Optional, Union

import numpy as np


class EMAFilter:

    def __init__(self, alpha: float):
        self.alpha = alpha
        self.prev: Optional[Union[float, np.ndarray]] = None

    def update(self, val):
        if self.prev is None:
            self.prev = val
        else:
            self.prev = self.alpha * val + (1.0 - self.alpha) * self.prev
        return self.prev

    def reset(self):
        self.prev = None


class HysteresisGate:

    def __init__(self, thr_on: float, thr_off: float):
        self.thr_on = thr_on
        self.thr_off = thr_off
        self.state = False

    def update(self, val: float) -> bool:
        if not self.state and val >= self.thr_on:
            self.state = True
        elif self.state and val < self.thr_off:
            self.state = False
        return self.state

    def set_thresholds(self, thr_on: float, thr_off: float):
        self.thr_on = thr_on
        self.thr_off = thr_off
