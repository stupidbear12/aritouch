# config.py
import os, json

_DEFAULT = {
    # 기본 동작
    "smoothing": 0.3,
    "mirror": False,
    "camera_index": 0,
    "use_cap_dshow": True,

    # 터치(z) 판정 파라미터
    "tmin_ms": 120,
    "vmax_px": 35,
    "k_in": 2.0,
    "k_out": 1.0,
    "margin": 0.005,
    "alpha_base": 0.02,
    "alpha_sigma": 0.02,

    # 터치 시 클릭 여부
    "click_on_touch": False,

    # 터치 극성: "neg" | "pos" | "auto"
    # - neg: 다가오면 dz가 음수
    # - pos: 다가오면 dz가 양수
    # - auto: 관측값으로 자동 추정
    "touch_polarity": "auto",

    # 핀치 줌
    "zoom_gain": 1.6,          # 핀치 변화 → 휠틱 스케일
    "wheel_step": 120,         # 윈도우 휠 한 틱
    "pinch_deadzone": 0.004,   # 미세 떨림 무시
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
