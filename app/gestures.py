# DEPRECATED: Replaced by gesture/ modular pipeline (gesture_applier, candidate_scorer, etc.)
# Kept for reference only. Use core/mediapipe_runner.py + gesture/ modules in new code.
from math import hypot
from utils.geometry import clamp
from control.mouse_actions import MouseController
from control.zoom_actions import ZoomActions

class TouchZoomController:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.z0 = None
        self.sigma = 0.0
        self.touching = False
        self.enter_ms = 0
        self.last_pos = None
        self.last_sent_move = None
        self.move_threshold = 1
        self.pinch_d0 = None
        self.pinch_accum = 0.0
        self.mouse = MouseController()
        self.zoom_actions = ZoomActions(wheel_step=int(cfg.get("wheel_step", 120)))
        self.polarity = None
        self._dz_ema = 0.0
        self._dz_alpha = 0.15

    def _update_baseline(self, zf, move_px):
        if self.z0 is None:
            self.z0 = zf
            self.sigma = 0.0
            return
        a_base = float(self.cfg["alpha_base"])
        a_sig  = float(self.cfg["alpha_sigma"])
        if (not self.touching) or (move_px >= self.cfg["vmax_px"]):
            self.z0    = (1 - a_base) * self.z0 + a_base * zf
            self.sigma = (1 - a_sig ) * self.sigma + a_sig * abs(zf - self.z0)

    def _pinch_distance_norm(self, ix, iy, tx, ty):
        return hypot(ix - tx, iy - ty)

    def update(self, nx, ny, nz, tx, ty, tz, Xs, Ys, now_ms, SW, SH):
        if self.last_pos is None:
            move_px = 0.0
        else:
            move_px = hypot(Xs - self.last_pos[0], Ys - self.last_pos[1])
        self.last_pos = (Xs, Ys)

        self._update_baseline(nz, move_px)

        zf = nz
        dz = None if self.z0 is None else (zf - self.z0)
        delta_in  = None if self.z0 is None else (self.cfg["k_in"]  * self.sigma + self.cfg["margin"])
        delta_out = None if self.z0 is None else (self.cfg["k_out"] * self.sigma + self.cfg["margin"])

        pol_cfg = (self.cfg.get("touch_polarity") or "auto").lower()
        if dz is not None:
            self._dz_ema = (1 - self._dz_alpha) * self._dz_ema + self._dz_alpha * dz
            if pol_cfg == "auto":
                if abs(self._dz_ema) > 1e-4:
                    self.polarity = "neg" if self._dz_ema < 0 else "pos"
            else:
                self.polarity = "neg" if pol_cfg == "neg" else "pos"

        def enter_condition(dz_val, din):
            if self.polarity == "pos":
                return dz_val is not None and din is not None and dz_val >= din
            return dz_val is not None and din is not None and dz_val <= -din

        def exit_condition(dz_val, dout):
            if self.polarity == "pos":
                return dz_val is not None and dout is not None and dz_val <= dout
            return dz_val is not None and dout is not None and dz_val >= -dout

        if (self.z0 is not None) and (dz is not None):
            if not self.touching:
                if enter_condition(dz, delta_in) and (move_px <= self.cfg["vmax_px"]):
                    if self.enter_ms == 0:
                        self.enter_ms = now_ms
                    elif now_ms - self.enter_ms >= self.cfg["tmin_ms"]:
                        self.touching = True
                        self.enter_ms = 0
                        self.pinch_d0 = self._pinch_distance_norm(nx, ny, tx, ty)
                        self.pinch_accum = 0.0
                        if self.cfg["click_on_touch"]:
                            self.mouse.click_left()
                else:
                    self.enter_ms = 0
            else:
                if exit_condition(dz, delta_out):
                    self.touching = False
                    self.pinch_d0 = None
                    self.pinch_accum = 0.0

        if self.cfg["zoom_center_follow_cursor"] or not self.touching:
            if (self.last_sent_move is None or
                abs(Xs - self.last_sent_move[0]) >= self.move_threshold or
                abs(Ys - self.last_sent_move[1]) >= self.move_threshold):
                self.mouse.move_to(Xs, Ys)
                self.last_sent_move = (Xs, Ys)

        pinch_d = None
        zoom_ticks_sent = 0
        if self.touching and (self.pinch_d0 is not None):
            pinch_d = self._pinch_distance_norm(nx, ny, tx, ty)
            delta = pinch_d - self.pinch_d0
            dd = 0.0 if abs(delta) < self.cfg["pinch_deadzone"] else delta
            self.pinch_accum += dd * self.cfg["zoom_gain"]
            ticks = int(self.pinch_accum)
            if ticks != 0:
                self.zoom_actions.scroll_with_ctrl(ticks)
                zoom_ticks_sent = ticks
                self.pinch_accum -= ticks

        return {
            "z0": self.z0, "sigma": self.sigma, "dz": dz,
            "delta_in": delta_in, "delta_out": delta_out,
            "touching": self.touching,
            "pinch_d0": self.pinch_d0, "pinch_d": pinch_d,
            "zoom_ticks": zoom_ticks_sent,
            "polarity": self.polarity or pol_cfg
        }
