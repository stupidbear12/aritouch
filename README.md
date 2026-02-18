AirTouch
========

손 제스처로 마우스와 키보드를 제어하는 Windows 전용 애플리케이션입니다.  
웹캠과 MediaPipe를 사용해 얼굴/손을 인식하고, 클릭·드래그·스크롤·줌·가상 키보드 입력을 지원합니다.

## 주요 기능

- **터치 모드 (Touch Mode)**  
  - 검지/중지 제스처로 **클릭 / 드래그 / 더블클릭**  
  - Pinch 제스처(검지–엄지)로 **Ctrl+Wheel 기반 Zoom In/Out**  
  - 양손 Pinch 제스처로 **수직/수평 스크롤**  
  - 얼굴–손 Z 거리 기반 **ACTIVE / IDLE 상태 전환 및 히스테리시스 제어**

- **키보드 모드 (Keyboard Mode)**  
  - 화면 하단에 **가상 키보드** 표시  
  - 검지 MCP 위치로 키를 가리키고, 손가락을 구부려 **키 입력**  
  - 입력/표시 토글, 쿨다운, 시각적 피드백 등 제공

- **모드 전환 제스처**  
  - Shaka 제스처(엄지·새끼만 펴고 나머지 손가락은 접은 상태)를 **2초간 유지**하면  
    **터치 모드 ↔ 키보드 모드** 전환

- **빌드 및 배포**  
  - `PyInstaller`를 이용해 단일 실행 파일로 빌드 (`airtouch.spec`)  
  - Inno Setup 스크립트(`airtouch.iss`)로 설치 프로그램 생성  
  - `build.bat` 에 PyInstaller 빌드 및 Inno Setup 호출 자동화

## 시스템 요구 사항

- **OS**: Windows 10 이상 (x64)  
- **필수 하드웨어**: 웹캠  
- **Python**: 3.10 이상 권장  
- **의존성**:  
  - `mediapipe`  
  - `opencv-python`  
  - `numpy`  
  - `pywin32` (마우스/키보드 제어용)  
  - `pyautogui`

## 설치

```bash
git clone https://github.com/your-name/aritouch.git
cd aritouch
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> 실제 리포지토리 URL과 Python 버전은 환경에 맞게 수정하세요.

## 실행 방법

기본 AirTouch 애플리케이션은 `main.py` 입니다.

```bash
python main.py
```

실행 후 웹캠이 켜지며, 거울 모드로 카메라 영상과 HUD가 표시됩니다.

## 조작 방법

- **공통**
  - `q` : 프로그램 종료
  - Shaka 제스처를 2초간 유지 : **Touch ↔ Keyboard 모드 전환**

- **터치 모드 (Touch Mode)**
  - `c` : 커서 ON/OFF 토글  
  - `m` : 커서 좌우 반전 (mirror)  
  - `n` : 원근 보정 ON/OFF  
  - `r` : Z 기준선(baseline) 리셋  
  - 검지 각도 기반 **클릭**, 중지 각도 기반 **드래그 시작/종료**  
  - 검지–엄지 Pinch 거리로 **Zoom In/Out** (Ctrl + Wheel)  
  - 양손 Pinch + 엄지 이동으로 **스크롤 (상/하/좌/우)**

- **키보드 모드 (Keyboard Mode)**
  - `t` : 실제 키 입력 ON/OFF  
  - `k` : 가상 키보드 표시 ON/OFF  
  - 검지 MCP로 키를 가리키고 손가락을 구부려 입력  
  - HUD에 현재 타이핑/키보드 상태, Hover 중인 키, 클릭 상태 표시

## 프로젝트 구조

- `main.py`  
  - AirTouch V6 메인 엔트리 포인트.  
  - 얼굴/손 검출, 모드 전환, ACTIVE/IDLE 상태, Zoom/Scroll/가상 키보드 제어를 모두 통합.

- `config.py`  
  - 앱 메타데이터, 경로 설정(PyInstaller/포터블 대응), 로그/설정 파일 위치.  
  - 웹캠/MediaPipe/제스처/EMA/Zoom/커서/HUD 관련 상수 정의.

- `gesture/`  
  - `detector.py` : `FaceDetector`, `HandDetector`  
    - MediaPipe FaceMesh/Hands 래퍼, 얼굴·손 랜드마크 2D/3D/정규화 좌표 제공.  
  - `recognizer.py` : `FingerGestureRecognizer`, `PinchRecognizer`, `ShakaModeRecognizer`  
    - 손가락 각도 기반 클릭/드래그 판정, Pinch 거리 계산, Shaka 모드 전환 제스처 인식.

- `control/`  
  - `cursor.py` : `CursorMapper`, `SystemCursorChanger`  
    - 손 좌표를 화면 좌표로 매핑(EMA 필터+mirror+threshold), Windows 시스템 커서 모양 변경.  
  - `mouse.py` : `MouseController`, `ClickManager`  
    - 클릭/더블클릭/드래그 구현 및 불응기·더블클릭 홀드 관리.  
  - `zoom.py` : `ZoomController`, `PinchZoomManager`, `ZoomGuard`  
    - Ctrl+Wheel Zoom, Pinch 거리→Zoom 스텝 변환, 원근 보정 및 보호 로직.  
  - `keyboard.py` : `VirtualKeyboard`  
    - 화면 하단 QWERTY 스타일 가상 키보드 렌더링 및 제스처 기반 타이핑.

- `scroll.py`  
  - `ScrollGestureManager`  
  - 양손 Pinch + 엄지 이동을 이용해 수직/수평 스크롤 이벤트를 발생.

- `state/`  
  - `manager.py`  
    - `StateManager` : Z 거리 EMA + 히스테리시스로 ACTIVE/IDLE 판정 및 튜닝 파라미터 관리.  
    - `ModeManager` : Touch / Keyboard 모드 전환 및 현재 모드 조회.

- `filters/ema_filter.py`  
  - `EMAFilter`, `MultiEMAFilter` : 단일 값 및 다차원 값에 대한 지수 이동 평균 필터.

- `utils/math_utils.py`  
  - `clamp`, `l2_distance`, `angle_at_joint`, 좌표 정규화/역정규화 유틸.

- `test_shaka_gesture.py`  
  - Shaka 제스처 인식 및 진행률/손가락 각도 디버깅용 독립 테스트 앱.

- `virtual_keyboard_typing_1.py`, `vkeyboard.py`  
  - 다양한 형태(모바일 스타일, TKL 레이아웃)의 **실험용 가상 키보드** 구현.  
  - 본 실행 흐름(`main.py`)에서 직접 사용되지는 않으며, 연구/데모 목적.

- `airtouch.spec`, `main.spec`  
  - PyInstaller 빌드 스펙 파일. (`airtouch.spec`가 최신/권장)

- `airtouch.iss`, `installer/setup.iss`  
  - Inno Setup 설치 프로그램 스크립트 (신규/기존 버전).

- `build.bat`  
  - Python 실행 파일 탐색 → PyInstaller 빌드 → Inno Setup 호출까지 자동화.

## 빌드 & 설치 파일 생성

1. 의존성 설치 후, Windows에서 다음을 실행:

   ```bat
   build.bat
   ```

2. 성공 시:
   - `dist\AirTouch\AirTouch.exe` : 포터블 실행 파일  
   - `dist\installer\AirTouch_Setup_*.exe` : 설치 프로그램 (Inno Setup 사용)

> Inno Setup 이 설치되어 있지 않으면, 로그에 경고만 출력되고 실행 파일 빌드까지만 수행됩니다.

## 코드 품질 및 개선 여지 (요약)

- 전반적으로 **모듈 분리가 잘 되어 있고**, 각 클래스/함수에 한글+영문 Docstring이 있어 유지보수성이 좋습니다.  
- `control`, `gesture`, `state`, `filters`, `utils` 계층이 명확해 메인 로직(`AirTouchApp`)이 비교적 읽기 쉽습니다.  
- 실험용 스크립트(`virtual_keyboard_typing_1.py`, `vkeyboard.py`, `test_shaka_gesture.py`)는 현재 구조와 별개로 동작하므로,  
  배포용 빌드에서 제외하거나 `examples/` 디렉터리로 분리하면 더 깔끔합니다.  
- 예외 처리와 로깅(특히 MediaPipe/캠 Fail, win32 미사용 환경)에 대한 공통 로거 도입을 고려할 수 있습니다.
