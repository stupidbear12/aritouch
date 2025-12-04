import cv2
import numpy as np
import time
import math
import ctypes

try:
    import win32api, win32con
    WINDOWS = True
except Exception:
    WINDOWS = False

import mediapipe as mp


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class VirtualKeyboardWithGesture:
    """
    제스처 기반 가상 키보드
    - 검지 MCP 좌표로 커서 위치 결정
    - 검지를 구부리는 제스처로 키 입력
    - 양손 감지 및 독립적 입력 가능
    """
    
    # Face mesh landmarks
    R_EYE_OUTER = 33
    R_EYE_INNER = 133
    L_EYE_OUTER = 263
    L_EYE_INNER = 362
    
    # 키보드 레이아웃 정의 (휴대폰 스타일)
    KEYBOARD_LAYOUT = {
        'row0': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],  # 숫자
        'row1': ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],  # QWERTY
        'row2': ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],       # ASDF
        'row3': ['SHIFT', 'z', 'x', 'c', 'v', 'b', 'n', 'm', 'BKSP'],  # ZXCV + Shift/Backspace
        'row4': ['!#1', ',', 'SPACE', '.', 'ENTER']  # 하단 행
    }
    
    # 키 색상
    KEY_COLOR_NORMAL = (70, 70, 70)
    KEY_COLOR_HOVER = (100, 150, 100)
    KEY_COLOR_PRESSED = (50, 200, 50)
    TEXT_COLOR = (255, 255, 255)

    def __init__(self,
                 cam_index=0, 
                 cam_w=1280, 
                 cam_h=720,
                 det_conf_face=0.5,
                 det_conf_hand=0.7, 
                 track_conf_hand=0.6,
                 key_size=50,
                 key_spacing=6,
                 keyboard_y_start=250,
                 click_angle_threshold=150.0,
                 release_angle_threshold=165.0):
        
        # 카메라 설정
        self.cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_h)
        self.frame_w = cam_w
        self.frame_h = cam_h

        # MediaPipe 초기화
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=det_conf_face,
            min_tracking_confidence=0.5
        )
        
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=det_conf_hand,
            min_tracking_confidence=track_conf_hand
        )
        
        self.drawer = mp.solutions.drawing_utils
        
        # 키보드 설정
        self.key_size = key_size
        self.key_spacing = key_spacing
        self.keyboard_y_start = keyboard_y_start
        self.key_rects = {}
        self._build_keyboard_layout()
        
        # 제스처 감지 설정
        self.click_angle_threshold = click_angle_threshold  # 이 각도 이하면 클릭
        self.release_angle_threshold = release_angle_threshold  # 이 각도 이상이면 릴리즈
        
        # 타이핑 상태
        self.typing_enabled = True
        self.show_keyboard = True
        self.show_angle_info = True
        self.last_key_press = {}
        self.key_cooldown_ms = 300
        
        # 각 손가락의 클릭 상태 추적
        self.finger_click_state = {}  # {hand_idx: bool}
        
        # 시각화
        self.hovered_keys = {}  # {hand_idx: key_char}
        self.pressed_keys = {}  # {key_char: timestamp}

        if WINDOWS:
            self.SW = win32api.GetSystemMetrics(0)
            self.SH = win32api.GetSystemMetrics(1)
        else:
            self.SW, self.SH = 1920, 1080

    def _build_keyboard_layout(self):
        """휴대폰 스타일 키보드 레이아웃 좌표 계산"""
        self.key_rects = {}
        
        # 키보드 전체를 화면 중앙에 배치
        keyboard_width = self.key_size * 10 + self.key_spacing * 9
        start_x = (self.frame_w - keyboard_width) // 2
        
        y = self.keyboard_y_start
        
        # Row 0: 숫자 행 (1-9, 0)
        x = start_x
        for key in self.KEYBOARD_LAYOUT['row0']:
            w = self.key_size
            h = self.key_size
            self.key_rects[key] = (x, y, w, h)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing
        
        # Row 1: QWERTY 행
        x = start_x
        for key in self.KEYBOARD_LAYOUT['row1']:
            w = self.key_size
            h = self.key_size
            self.key_rects[key] = (x, y, w, h)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing
        
        # Row 2: ASDF 행 (약간 오른쪽으로 시프트)
        x = start_x + self.key_size // 2
        for key in self.KEYBOARD_LAYOUT['row2']:
            w = self.key_size
            h = self.key_size
            self.key_rects[key] = (x, y, w, h)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing
        
        # Row 3: ZXCV 행 + SHIFT, BACKSPACE
        x = start_x
        for i, key in enumerate(self.KEYBOARD_LAYOUT['row3']):
            if key == 'SHIFT':
                w = int(self.key_size * 1.3)
            elif key == 'BKSP':
                w = int(self.key_size * 1.3)
            else:
                w = self.key_size
            
            h = self.key_size
            self.key_rects[key] = (x, y, w, h)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing
        
        # Row 4: 하단 행 (!#1, 쉼표, SPACE, 마침표, ENTER)
        x = start_x
        for key in self.KEYBOARD_LAYOUT['row4']:
            if key == '!#1':
                w = int(self.key_size * 1.2)
            elif key == 'SPACE':
                w = int(self.key_size * 4.5)
            elif key == 'ENTER':
                w = int(self.key_size * 1.5)
            else:
                w = self.key_size
            
            h = self.key_size
            self.key_rects[key] = (x, y, w, h)
            x += w + self.key_spacing

    def _get_eye_midpoint(self, face, w, h):
        """양안 중점 계산"""
        lm = face.landmark
        
        r_outer = np.array([lm[self.R_EYE_OUTER].x * w, lm[self.R_EYE_OUTER].y * h])
        r_inner = np.array([lm[self.R_EYE_INNER].x * w, lm[self.R_EYE_INNER].y * h])
        r_center = 0.5 * (r_outer + r_inner)
        
        l_outer = np.array([lm[self.L_EYE_OUTER].x * w, lm[self.L_EYE_OUTER].y * h])
        l_inner = np.array([lm[self.L_EYE_INNER].x * w, lm[self.L_EYE_INNER].y * h])
        l_center = 0.5 * (l_outer + l_inner)
        
        eye_midpoint = 0.5 * (r_center + l_center)
        
        return eye_midpoint

    def _get_index_finger_data(self, hand_landmarks_list, w, h):
        """양손의 검지 손가락 데이터 추출 (MCP 위치 + 각도)"""
        finger_data_list = []
        
        for hand_idx, hand in enumerate(hand_landmarks_list):
            lm = hand.landmark
            
            # 검지 관절 좌표
            idx_mcp = mp.solutions.hands.HandLandmark.INDEX_FINGER_MCP
            idx_pip = mp.solutions.hands.HandLandmark.INDEX_FINGER_PIP
            idx_dip = mp.solutions.hands.HandLandmark.INDEX_FINGER_DIP
            idx_tip = mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP
            
            # MCP 위치 (커서 위치로 사용)
            mcp_x = lm[idx_mcp].x * w
            mcp_y = lm[idx_mcp].y * h
            
            # 각도 계산을 위한 좌표
            mcp_pos = np.array([lm[idx_mcp].x * w, lm[idx_mcp].y * h])
            pip_pos = np.array([lm[idx_pip].x * w, lm[idx_pip].y * h])
            dip_pos = np.array([lm[idx_dip].x * w, lm[idx_dip].y * h])
            tip_pos = np.array([lm[idx_tip].x * w, lm[idx_tip].y * h])
            
            # 검지 구부림 각도 계산 (PIP 관절 기준)
            finger_angle = self._calculate_angle(mcp_pos, pip_pos, dip_pos)
            
            finger_data_list.append({
                'hand_idx': hand_idx,
                'mcp_pos': np.array([mcp_x, mcp_y]),  # 커서 위치
                'angle': finger_angle,  # 구부림 각도
                'mcp': mcp_pos,
                'pip': pip_pos,
                'dip': dip_pos,
                'tip': tip_pos
            })
        
        return finger_data_list

    def _calculate_angle(self, a, b, c):
        """세 점으로 이루어진 각도 계산 (b가 중심점)"""
        v1 = a - b
        v2 = c - b
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 180.0
        
        cos_angle = np.dot(v1, v2) / (norm1 * norm2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        angle_rad = np.arccos(cos_angle)
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg

    def _check_key_collision(self, finger_pos, key_char):
        """손가락과 키 충돌 감지"""
        if key_char not in self.key_rects:
            return False
        
        fx, fy = finger_pos
        kx, ky, kw, kh = self.key_rects[key_char]
        
        return (kx <= fx <= kx + kw) and (ky <= fy <= ky + kh)

    def _detect_click_gesture(self, finger_data):
        """검지 구부리기 제스처로 클릭 감지"""
        hand_idx = finger_data['hand_idx']
        angle = finger_data['angle']
        
        # 이전 상태 가져오기
        was_clicking = self.finger_click_state.get(hand_idx, False)
        
        # 클릭 판정
        if angle <= self.click_angle_threshold and not was_clicking:
            # 손가락을 구부렸고, 이전에는 클릭 상태가 아니었음 → 클릭 시작
            self.finger_click_state[hand_idx] = True
            return True
        elif angle >= self.release_angle_threshold and was_clicking:
            # 손가락을 펴고, 이전에는 클릭 상태였음 → 릴리즈
            self.finger_click_state[hand_idx] = False
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
        if not WINDOWS or not self.typing_enabled:
            return
        
        try:
            # 특수 키 매핑
            if key_char == 'SPACE':
                vk_code = win32con.VK_SPACE
            elif key_char == 'BKSP':
                vk_code = win32con.VK_BACK
            elif key_char == 'ENTER':
                vk_code = win32con.VK_RETURN
            elif key_char == 'SHIFT':
                # Shift는 토글 방식으로 처리 (대소문자 전환)
                print(f"[SHIFT] Toggle (implement shift state if needed)")
                return
            elif key_char == '!#1':
                # 특수기호 모드 전환
                print(f"[SPECIAL] Toggle special characters mode")
                return
            elif key_char.isalpha():
                # 알파벳
                vk_code = ord(key_char.upper())
            elif key_char.isdigit():
                # 숫자
                vk_code = ord(key_char)
            elif key_char == ',':
                vk_code = win32con.VK_OEM_COMMA
            elif key_char == '.':
                vk_code = win32con.VK_OEM_PERIOD
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
            elif key_char in self.hovered_keys.values():
                color = self.KEY_COLOR_HOVER
            else:
                color = self.KEY_COLOR_NORMAL
            
            # 키 박스
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (200, 200, 200), 2)
            
            # 키 텍스트
            if key_char == 'SPACE':
                text = ''  # 스페이스바는 빈 공간
                font_scale = 0.5
            elif key_char == 'BKSP':
                text = '←'
                font_scale = 0.8
            elif key_char == 'SHIFT':
                text = '⇧'
                font_scale = 0.8
            elif key_char == 'ENTER':
                text = '↵'
                font_scale = 0.8
            elif key_char == '!#1':
                text = '!#1'
                font_scale = 0.5
            elif key_char.isdigit():
                text = key_char
                font_scale = 0.7
            else:
                text = key_char
                font_scale = 0.7
            
            if text:  # 텍스트가 있을 때만 그리기
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
                text_x = x + (w - text_size[0]) // 2
                text_y = y + (h + text_size[1]) // 2
                cv2.putText(frame, text, (text_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.TEXT_COLOR, 2)
        
        return frame

    def process_frame(self, frame):
        """프레임 처리"""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        face_res = self.face_mesh.process(rgb)
        hand_res = self.hands.process(rgb)
        
        hud = []
        eye_midpoint = None
        
        # 얼굴 감지
        if face_res.multi_face_landmarks:
            face = face_res.multi_face_landmarks[0]
            eye_midpoint = self._get_eye_midpoint(face, w, h)
            cv2.circle(frame, (int(eye_midpoint[0]), int(eye_midpoint[1])), 8, (0, 200, 255), -1)
        
        # 손 감지
        self.hovered_keys = {}
        
        if hand_res.multi_hand_landmarks:
            # 손 랜드마크 그리기
            for hand in hand_res.multi_hand_landmarks:
                self.drawer.draw_landmarks(
                    frame, 
                    hand, 
                    mp.solutions.hands.HAND_CONNECTIONS,
                    mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                    mp.solutions.drawing_styles.get_default_hand_connections_style()
                )
            
            # 검지 손가락 데이터 추출
            finger_data_list = self._get_index_finger_data(hand_res.multi_hand_landmarks, w, h)
            
            for finger_data in finger_data_list:
                hand_idx = finger_data['hand_idx']
                mcp_pos = finger_data['mcp_pos']
                angle = finger_data['angle']
                mcp = finger_data['mcp']
                pip = finger_data['pip']
                dip = finger_data['dip']
                tip = finger_data['tip']
                
                # 검지 MCP 위치 표시 (커서)
                cv2.circle(frame, (int(mcp_pos[0]), int(mcp_pos[1])), 12, (255, 0, 255), -1)
                cv2.circle(frame, (int(mcp_pos[0]), int(mcp_pos[1])), 15, (255, 0, 255), 2)
                
                # 검지 관절 선 그리기
                cv2.line(frame, tuple(mcp.astype(int)), tuple(pip.astype(int)), (0, 255, 0), 2)
                cv2.line(frame, tuple(pip.astype(int)), tuple(dip.astype(int)), (0, 255, 0), 2)
                cv2.line(frame, tuple(dip.astype(int)), tuple(tip.astype(int)), (0, 255, 0), 2)
                
                # 양안 중점에서 MCP까지 선
                if eye_midpoint is not None:
                    cv2.line(frame, 
                            (int(eye_midpoint[0]), int(eye_midpoint[1])),
                            (int(mcp_pos[0]), int(mcp_pos[1])),
                            (255, 0, 255), 2)
                
                # 각도 정보 표시
                if self.show_angle_info:
                    is_clicking = self.finger_click_state.get(hand_idx, False)
                    angle_text = f"{angle:.1f}deg"
                    angle_color = (0, 255, 0) if is_clicking else (255, 255, 255)
                    cv2.putText(frame, angle_text,
                               (int(mcp_pos[0]) + 20, int(mcp_pos[1])),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, angle_color, 2)
                
                # 키 충돌 감지 (MCP 위치 기준)
                for key_char in self.key_rects.keys():
                    if self._check_key_collision(mcp_pos, key_char):
                        self.hovered_keys[hand_idx] = key_char
                        
                        # 클릭 제스처 감지
                        is_click = self._detect_click_gesture(finger_data)
                        
                        if is_click and self._can_press_key(key_char):
                            self._type_key(key_char)
                        
                        break
        
        # 키보드 그리기
        frame = self._draw_keyboard(frame)
        
        # HUD 정보
        hud.append("=== MOBILE-STYLE KEYBOARD (GESTURE) ===")
        hud.append(f"Typing: {'ON' if self.typing_enabled else 'OFF'} | Keyboard: {'ON' if self.show_keyboard else 'OFF'}")
        hud.append(f"Face: {'YES' if eye_midpoint is not None else 'NO'} | Hands: {len(hand_res.multi_hand_landmarks) if hand_res.multi_hand_landmarks else 0}/2")
        hud.append(f"Click Angle: <{self.click_angle_threshold:.0f}° | Release: >{self.release_angle_threshold:.0f}°")
        
        # 호버 중인 키
        if self.hovered_keys:
            hover_text = " | ".join([f"H{k}: {v}" for k, v in self.hovered_keys.items()])
            hud.append(f"Hovering: {hover_text}")
        
        # 클릭 상태
        clicking = [f"H{k}" for k, v in self.finger_click_state.items() if v]
        if clicking:
            hud.append(f"Clicking: {', '.join(clicking)}")
        
        return frame, hud

    def run(self):
        """메인 실행 루프"""
        if not self.cap.isOpened():
            print("Failed to open webcam.")
            return
        
        print("=" * 70)
        print("MOBILE-STYLE VIRTUAL KEYBOARD - GESTURE BASED")
        print("=" * 70)
        print("Controls:")
        print("  q: Quit")
        print("  t: Toggle typing ON/OFF")
        print("  k: Toggle keyboard display ON/OFF")
        print("  a: Toggle angle info ON/OFF")
        print("  +/-: Adjust click angle threshold")
        print("")
        print("Layout:")
        print("  - Numbers: 1-0")
        print("  - QWERTY keyboard")
        print("  - Special keys: Shift, Backspace, Enter")
        print("  - Symbols: !#1, comma, period")
        print("")
        print("How to type:")
        print("  1. Position your INDEX FINGER MCP over a key")
        print("  2. CURL your index finger (bend it)")
        print("  3. When angle < threshold, key is typed!")
        print("  4. Straighten finger to release")
        print("")
        print("Tip: MCP (knuckle) determines position!")
        print("=" * 70)
        
        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break
                
                frame = cv2.flip(frame, 1)
                out, hud = self.process_frame(frame)
                
                # HUD 텍스트 표시
                y = 30
                for text in hud:
                    # 배경
                    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(out, (5, y - 22), (15 + text_w, y + 5), (0, 0, 0), -1)
                    
                    # 텍스트
                    if "ON" in text or "YES" in text:
                        color = (0, 255, 0)
                    elif "MOBILE" in text:
                        color = (0, 255, 255)
                    else:
                        color = (255, 255, 255)
                    
                    cv2.putText(out, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    y += 28
                
                cv2.imshow("Mobile-Style Virtual Keyboard", out)
                
                # 키 입력
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('t'):
                    self.typing_enabled = not self.typing_enabled
                    print(f"Typing: {'ON' if self.typing_enabled else 'OFF'}")
                elif key == ord('k'):
                    self.show_keyboard = not self.show_keyboard
                    print(f"Keyboard display: {'ON' if self.show_keyboard else 'OFF'}")
                elif key == ord('a'):
                    self.show_angle_info = not self.show_angle_info
                    print(f"Angle info: {'ON' if self.show_angle_info else 'OFF'}")
                elif key == ord('+') or key == ord('='):
                    self.click_angle_threshold = min(180.0, self.click_angle_threshold + 5.0)
                    print(f"Click angle threshold: {self.click_angle_threshold:.0f}°")
                elif key == ord('-') or key == ord('_'):
                    self.click_angle_threshold = max(90.0, self.click_angle_threshold - 5.0)
                    print(f"Click angle threshold: {self.click_angle_threshold:.0f}°")
        
        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            print("\nVirtual Keyboard terminated.")


def main():
    app = VirtualKeyboardWithGesture(
        cam_index=0,
        cam_w=1280,
        cam_h=720,
        det_conf_face=0.5,
        det_conf_hand=0.7,
        track_conf_hand=0.6,
        key_size=50,  # 키 크기 조정
        key_spacing=6,  # 간격 조정
        keyboard_y_start=250,  # 키보드 시작 위치 (더 위로)
        click_angle_threshold=150.0,  # 이 각도 이하로 구부리면 클릭
        release_angle_threshold=165.0  # 이 각도 이상으로 펴면 릴리즈
    )
    app.run()


if __name__ == "__main__":
    main()