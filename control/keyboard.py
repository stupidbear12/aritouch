"""
Virtual Keyboard Control Module
제스처 기반 가상 키보드 제어
"""

import cv2
import numpy as np
import time

try:
    import win32api
    import win32con
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    print("Warning: win32api not available. Keyboard typing disabled.")

from utils.math_utils import angle_at_joint


class VirtualKeyboard:
    """
    제스처 기반 가상 키보드
    - 검지 MCP 좌표로 커서 위치 결정
    - 검지를 구부리는 제스처로 키 입력
    """

    # 키보드 레이아웃 정의
    KEYBOARD_LAYOUT = {
        'row1': ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
        'row2': ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
        'row3': ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
        'row4': ['SPACE', 'BACKSPACE']
    }

    # 키 색상
    KEY_COLOR_NORMAL = (70, 70, 70)
    KEY_COLOR_HOVER = (100, 150, 100)
    KEY_COLOR_PRESSED = (50, 200, 50)
    TEXT_COLOR = (255, 255, 255)

    def __init__(self,
                 frame_width=1280,
                 frame_height=720,
                 key_size=60,
                 key_spacing=10,
                 keyboard_y_start=400,
                 click_angle_threshold=150.0,
                 release_angle_threshold=165.0):

        self.frame_w = frame_width
        self.frame_h = frame_height

        # 키보드 설정
        self.key_size = key_size
        self.key_spacing = key_spacing
        self.keyboard_y_start = keyboard_y_start
        self.key_rects = {}
        self._build_keyboard_layout()

        # 제스처 감지 설정
        self.click_angle_threshold = click_angle_threshold
        self.release_angle_threshold = release_angle_threshold

        # 타이핑 상태
        self.typing_enabled = True
        self.show_keyboard = True
        self.last_key_press = {}
        self.key_cooldown_ms = 300

        # 클릭 상태 추적
        self.finger_click_state = False

        # 시각화
        self.hovered_key = None
        self.pressed_keys = {}  # {key_char: timestamp}

        self.windows_available = WINDOWS_AVAILABLE

    def _build_keyboard_layout(self):
        """키보드 레이아웃 좌표 계산"""
        self.key_rects = {}

        # 각 행의 시작 X 좌표
        row_starts = {
            'row1': 10,
            'row2': 10 + self.key_size // 2,
            'row3': 10 + self.key_size,
            'row4': 10 + self.key_size * 2
        }

        y = self.keyboard_y_start

        for row_idx, (row_name, keys) in enumerate(self.KEYBOARD_LAYOUT.items()):
            x = row_starts[row_name]

            for key in keys:
                if key == 'SPACE':
                    w = self.key_size * 5 + self.key_spacing * 4
                elif key == 'BACKSPACE':
                    w = self.key_size * 2 + self.key_spacing
                else:
                    w = self.key_size

                h = self.key_size

                self.key_rects[key] = (x, y, w, h)
                x += w + self.key_spacing

            y += self.key_size + self.key_spacing

    def _check_key_collision(self, finger_pos):
        """손가락과 키 충돌 감지"""
        fx, fy = finger_pos

        for key_char, (kx, ky, kw, kh) in self.key_rects.items():
            if (kx <= fx <= kx + kw) and (ky <= fy <= ky + kh):
                return key_char

        return None

    def _detect_click_gesture(self, index_angle):
        """검지 구부리기 제스처로 클릭 감지"""
        was_clicking = self.finger_click_state

        # 클릭 판정
        if index_angle <= self.click_angle_threshold and not was_clicking:
            # 손가락을 구부렸고, 이전에는 클릭 상태가 아니었음 → 클릭 시작
            self.finger_click_state = True
            return True
        elif index_angle >= self.release_angle_threshold and was_clicking:
            # 손가락을 펴고, 이전에는 클릭 상태였음 → 릴리즈
            self.finger_click_state = False
            return False

        return False

    def _can_press_key(self, key_char):
        """키 반복 입력 방지"""
        now_ms = int(time.time() * 1000)

        if key_char not in self.last_key_press:
            self.last_key_press[key_char] = now_ms
            return True

        if now_ms - self.last_key_press[key_char] > self.key_cooldown_ms:
            self.last_key_press[key_char] = now_ms
            return True

        return False

    def _type_key(self, key_char):
        """Win32 API를 사용한 실제 키 입력"""
        if not self.windows_available or not self.typing_enabled:
            return

        try:
            if key_char == 'SPACE':
                vk_code = win32con.VK_SPACE
            elif key_char == 'BACKSPACE':
                vk_code = win32con.VK_BACK
            elif key_char.isalpha():
                vk_code = ord(key_char.upper())
            else:
                return

            # 키 누름
            win32api.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.01)
            # 키 뗌
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)

            print(f"[TYPED] {key_char}")

            # 시각적 피드백
            self.pressed_keys[key_char] = time.time()

        except Exception as e:
            print(f"Typing error: {e}")

    def _draw_keyboard(self, frame):
        """화면에 가상 키보드 그리기"""
        if not self.show_keyboard:
            return frame

        # 반투명 배경
        overlay = frame.copy()
        cv2.rectangle(overlay,
                     (0, self.keyboard_y_start - 20),
                     (self.frame_w, self.frame_h),
                     (30, 30, 30),
                     -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        now = time.time()

        # 각 키 그리기
        for key_char, (x, y, w, h) in self.key_rects.items():
            # 키 색상 결정
            if key_char in self.pressed_keys and (now - self.pressed_keys[key_char] < 0.2):
                color = self.KEY_COLOR_PRESSED
            elif key_char == self.hovered_key:
                color = self.KEY_COLOR_HOVER
            else:
                color = self.KEY_COLOR_NORMAL

            # 키 박스
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (200, 200, 200), 2)

            # 키 텍스트
            if key_char == 'SPACE':
                text = '____SPACE____'
                font_scale = 0.6
            elif key_char == 'BACKSPACE':
                text = '<- BACK'
                font_scale = 0.6
            else:
                text = key_char
                font_scale = 0.8

            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
            text_x = x + (w - text_size[0]) // 2
            text_y = y + (h + text_size[1]) // 2
            cv2.putText(frame, text, (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.TEXT_COLOR, 2)

        return frame

    def process_keyboard_frame(self, frame, eye_midpoint, landmarks_2d):
        """
        키보드 모드 프레임 처리

        Args:
            frame: 비디오 프레임
            eye_midpoint: 양안 중점 좌표
            landmarks_2d: 손 랜드마크 2D 좌표

        Returns:
            frame: 처리된 프레임
        """
        h, w = frame.shape[:2]

        # 검지 MCP 위치 (커서)
        mcp_pos = landmarks_2d['idx_mcp']

        # 검지 MCP 표시
        cv2.circle(frame, (int(mcp_pos[0]), int(mcp_pos[1])), 12, (255, 0, 255), -1)
        cv2.circle(frame, (int(mcp_pos[0]), int(mcp_pos[1])), 15, (255, 0, 255), 2)

        # 검지 관절 선 그리기
        cv2.line(frame, tuple(landmarks_2d['idx_mcp'].astype(int)),
                tuple(landmarks_2d['idx_pip'].astype(int)), (0, 255, 0), 2)
        cv2.line(frame, tuple(landmarks_2d['idx_pip'].astype(int)),
                tuple(landmarks_2d['idx_dip'].astype(int)), (0, 255, 0), 2)
        cv2.line(frame, tuple(landmarks_2d['idx_dip'].astype(int)),
                tuple(landmarks_2d['idx_tip'].astype(int)), (0, 255, 0), 2)

        # 양안 중점에서 MCP까지 선
        if eye_midpoint is not None:
            cv2.line(frame,
                    (int(eye_midpoint[0]), int(eye_midpoint[1])),
                    (int(mcp_pos[0]), int(mcp_pos[1])),
                    (255, 0, 255), 2)

        # 검지 각도 계산
        index_angle = angle_at_joint(
            landmarks_2d['idx_mcp'],
            landmarks_2d['idx_pip'],
            landmarks_2d['idx_dip']
        )

        # 각도 표시
        angle_text = f"{index_angle:.1f}deg"
        angle_color = (0, 255, 0) if self.finger_click_state else (255, 255, 255)
        cv2.putText(frame, angle_text,
                   (int(mcp_pos[0]) + 20, int(mcp_pos[1])),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, angle_color, 2)

        # 키 충돌 감지
        self.hovered_key = self._check_key_collision(mcp_pos)

        if self.hovered_key:
            # 클릭 제스처 감지
            is_click = self._detect_click_gesture(index_angle)

            if is_click and self._can_press_key(self.hovered_key):
                self._type_key(self.hovered_key)

        # 키보드 그리기
        frame = self._draw_keyboard(frame)

        return frame

    def get_hud_info(self):
        """HUD 정보 반환"""
        info = []
        info.append(f"Typing: {'ON' if self.typing_enabled else 'OFF'}")
        info.append(f"Keyboard Display: {'ON' if self.show_keyboard else 'OFF'}")
        info.append(f"Click Angle: <{self.click_angle_threshold:.0f}deg")

        if self.hovered_key:
            info.append(f"Hovering: {self.hovered_key}")

        if self.finger_click_state:
            info.append("Status: CLICKING")

        return info

    def toggle_typing(self):
        """타이핑 활성화/비활성화"""
        self.typing_enabled = not self.typing_enabled
        return self.typing_enabled

    def toggle_keyboard_display(self):
        """키보드 표시 토글"""
        self.show_keyboard = not self.show_keyboard
        return self.show_keyboard
