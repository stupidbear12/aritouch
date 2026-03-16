import os, json

_DEFAULT = {
    "smoothing": 0.3,
    "mirror": False,
    "camera_index": 0,
    "use_cap_dshow": True,

    "tmin_ms": 120,
    "vmax_px": 35,
    "k_in": 2.0,
    "k_out": 1.0,
    "margin": 0.005,
    "alpha_base": 0.02,
    "alpha_sigma": 0.02,

    "click_on_touch": False,

    "touch_polarity": "auto",

    "zoom_gain": 1.6,
    "wheel_step": 120,
    "pinch_deadzone": 0.004,
    "zoom_center_follow_cursor": True
}

def load_config(json_path: str) -> dict:
    cfg = dict(_DEFAULT)
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                user = json.load(f) or {}
            if isinstance(user, dict):
                cfg.update(user)
        except Exception as e:
            print("config load error:", e)
    return cfg
