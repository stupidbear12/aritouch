"""
AirTouch Configuration
설정값과 상수 정의
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "AirTouch"
APP_VERSION = "5.0.0"
APP_AUTHOR = "AirTouch Lab"


def _resolve_base_dir() -> Path:
    """포터블/패키징 환경(PyInstaller)과 개발 환경 모두에서 기준 경로를 반환."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


BASE_DIR: Path = _resolve_base_dir()
DEFAULT_DATA_ROOT = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
APP_DATA_DIR = Path(os.environ.get("AIRTOUCH_DATA_DIR", DEFAULT_DATA_ROOT)).expanduser()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = APP_DATA_DIR / "airtouch.log"
SETTINGS_FILE = APP_DATA_DIR / "settings.json"
BUILD_OUTPUT_DIR = BASE_DIR / "dist"
INSTALLER_OUTPUT_DIR = BUILD_OUTPUT_DIR / "installer"


def resolve_resource(*parts: str) -> Path:
    """
    패키징 이후에도 안전하게 상대 경로 리소스를 얻기 위한 헬퍼.
    
    Args:
        parts: BASE_DIR 하위 경로 조합
    
    Returns:
        Path: 절대 경로
    """
    return BASE_DIR.joinpath(*parts)


def _configure_mediapipe_resources() -> None:
    """PyInstaller 환경에서 mediapipe가 모델 파일을 찾을 수 있도록 설정."""
    try:
        from mediapipe.python._framework_bindings import resource_util  # type: ignore
    except Exception:
        return

    for relative in (Path("_internal") / "mediapipe", Path("mediapipe")):
        candidate = BASE_DIR / relative
        if candidate.exists():
            try:
                resource_util.set_resource_dir(str(candidate))
            except Exception:
                pass
            break


_configure_mediapipe_resources()


# ===== 웹캠 설정 =====
CAM_INDEX = 0
CAM_WIDTH = 1280
CAM_HEIGHT = 720

# ===== MediaPipe 설정 =====
FACE_DETECTION_CONFIDENCE = 0.5
FACE_TRACKING_CONFIDENCE = 0.5
HAND_DETECTION_CONFIDENCE = 0.7
HAND_TRACKING_CONFIDENCE = 0.6
MAX_NUM_FACES = 1
MAX_NUM_HANDS = 2  # 스크롤 제스처를 위해 양손 검출

# ===== ACTIVE/IDLE 전환 설정 =====
FACTOR = 1.20                    # Z 거리 비율 (120%)
FACTOR_MIN = 0.3
FACTOR_MAX = 3.0
FACTOR_STEP = 0.2
Z_MARGIN = 5.0                   # 안전 마진 (픽셀)
HYSTERESIS_RATIO = 0.95          # 떨림 방지 (95%)

# ===== 제스처 인식 설정 =====
# 클릭
THETA_CLICK_IN = 150.0           # 150도 이하 → 클릭
THETA_CLICK_OUT = 165.0          # 165도 이상 → 클릭 해제

# 드래그
THETA_DRAG_IN = 150.0            # 150도 이하 → 드래그 시작
THETA_DRAG_OUT = 165.0           # 165도 이상 → 드래그 종료

# 더블클릭
DBL_HOLD_MS = 2000               # 2초 홀드 → 더블클릭
REFRACTORY_MS = 250              # 클릭 후 불응기

# ===== EMA 필터 설정 =====
EMA_LEN_ALPHA = 0.5              # Z 거리 EMA 계수
EMA_PINCH_ALPHA = 0.5            # Pinch 거리 EMA 계수
EMA_CURSOR_ALPHA = 0.6           # 커서 좌표 EMA 계수

# ===== 커서 설정 =====
MOVE_THRESHOLD = 1               # 커서 이동 최소 거리 (픽셀)
CURSOR_DEFAULT_ON = False        # 시작 시 커서 ON/OFF
MIRROR_DEFAULT = False           # 시작 시 좌우 반전

# ===== Zoom 설정 =====
PX_PER_STEP = 30.0               # Pinch 거리 → Wheel 스텝 변환 비율
DEADZONE_PX = 3.0                # Deadzone (픽셀)
MAX_STEPS_PER_FRAME = 6          # 프레임당 최대 Zoom 스텝
WHEEL_DELTA = 120                # 마우스 휠 1칸

# ===== Zoom 보호 설정 =====
ACTIVE_GRACE_MS = 180            # ACTIVE 진입 후 대기 시간
RELEASE_COOLDOWN_MS = 280        # IDLE 복귀 후 대기 시간
EDGE_BAND = 8.0                  # 경계 부근 보호 (픽셀)
DROP_GUARD = 12.0                # 급격한 Z 감소 보호 (픽셀)

# ===== 원근 보정 설정 =====
Z_NORMALIZATION_ENABLED = True   # 원근 보정 활성화
MIN_Z_FOR_NORMALIZATION = 20.0   # 최소 Z 거리 (0 나누기 방지)
REFERENCE_Z_FRAMES = 5           # 기준 Z 계산용 프레임 수

# ===== MediaPipe 랜드마크 인덱스 =====
# 얼굴 (FaceMesh 468개 점)
R_EYE_OUTER = 33
R_EYE_INNER = 133
L_EYE_OUTER = 263
L_EYE_INNER = 362

# ===== Windows 커서 상수 =====
SPI_SETCURSORS = 0x0057
IDC_ARROW = 32512
IDC_IBEAM = 32513
IDC_WAIT = 32514
IDC_CROSS = 32515
IDC_UPARROW = 32516
IDC_SIZEALL = 32646
IDC_NO = 32648
IDC_HAND = 32649
IDC_HELP = 32651

# ===== 커서 변경 설정 =====
CHANGE_CURSOR_ON_ACTIVE = True   # ACTIVE 시 커서 변경
ACTIVE_CURSOR_SHAPE = IDC_HAND   # ACTIVE 시 커서 모양

# ===== UI 설정 =====
WINDOW_NAME = "AirTouch - Virtual Touch Plane V5"
HUD_FONT = 0  # cv2.FONT_HERSHEY_SIMPLEX
HUD_FONT_SCALE = 0.8
HUD_FONT_THICKNESS = 2
HUD_LINE_HEIGHT = 26
HUD_START_Y = 26
HUD_COLOR_ACTIVE = (0, 255, 0)   # 초록색
HUD_COLOR_NORMAL = (255, 255, 255)  # 흰색

# ===== 키보드 단축키 안내 =====
HELP_TEXT = """
========================================
AirTouch V5 - Perspective Correction
========================================
Controls:
  q: quit
  c: toggle cursor ON/OFF
  m: mirror cursor (flip left/right)
  n: toggle Perspective Correction ON/OFF
  </>: adjust factor (ACTIVE sensitivity)
  [-]=: adjust z_margin and hysteresis
  r: reset baseline
========================================
"""