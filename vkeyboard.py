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


class VirtualKeyboardTKL:
    """
    텐키리스 키보드 레이아웃을 사용한 가상 키보드
    - 양안 중점 Z 좌표와 손가락 TIP Z 좌표 차이로 터치 감지
    - 임계값 이상 가까워지면 해당 좌표의 키 입력
    - 텐키리스(TKL) 키보드 레이아웃
    """
    
    # Face mesh landmarks for eyes
    R_EYE_OUTER = 33
    R_EYE_INNER = 133
    L_EYE_OUTER = 263
    L_EYE_INNER = 362
    
    # Hand landmarks for all finger tips
    FINGER_TIPS = [
        mp.solutions.hands.HandLandmark.THUMB_TIP,        # 4
        mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP,  # 8
        mp.solutions.hands.HandLandmark.MIDDLE_FINGER_TIP, # 12
        mp.solutions.hands.HandLandmark.RING_FINGER_TIP,   # 16
        mp.solutions.hands.HandLandmark.PINKY_TIP          # 20
    ]
    
    # 손가락 이름
    FINGER_NAMES = ['THUMB', 'INDEX', 'MIDDLE', 'RING', 'PINKY']
    
    # 손가락별 색상
    FINGER_COLORS = [
        (255, 0, 0),    # 엄지 - 파란색
        (0, 255, 0),    # 검지 - 초록색
        (0, 255, 255),  # 중지 - 노란색
        (255, 0, 255),  # 약지 - 자홍색
        (255, 128, 0)   # 새끼 - 주황색
    ]
    
    # 텐키리스 키보드 레이아웃
    KEYBOARD_LAYOUT = {
        'row0': ['ESC', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12'],
        'row1': ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'BKSP'],
        'row2': ['TAB', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\'],
        'row3': ['CAPS', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', "'", 'ENTER'],
        'row4': ['SHIFT', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'SHIFT'],
        'row5': ['CTRL', 'WIN', 'ALT', 'SPACE', 'ALT', 'CTRL'],
        'arrows': ['UP', 'LEFT', 'DOWN', 'RIGHT'],
        'edit': ['INS', 'HOME', 'PGUP', 'DEL', 'END', 'PGDN']
    }
    
    # 키 색상
    KEY_COLOR_NORMAL = (70, 70, 70)
    KEY_COLOR_HOVER = (100, 150, 100)
    KEY_COLOR_PRESSED = (50, 200, 50)
    KEY_COLOR_SPECIAL = (90, 70, 70)
    TEXT_COLOR = (255, 255, 255)

    def __init__(self,
                 cam_index=0, 
                 cam_w=1280, 
                 cam_h=720,
                 det_conf_face=0.5,
                 det_conf_hand=0.7, 
                 track_conf_hand=0.6,
                 key_size=35,
                 key_spacing=3,
                 keyboard_x_start=None,  # None이면 자동 중앙 정렬
                 keyboard_y_start=None,  # None이면 자동 중앙 정렬
                 z_push_threshold=0.10):  # Z축 밀어내기 감지 임계값 (높을수록 강하게 밀어야 함)
        
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
        
        # 양손 감지
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
        
        # 키보드를 화면 중앙에 배치
        if keyboard_x_start is None:
            # 키보드 예상 너비 계산 (대략적)
            estimated_width = int(key_size * 16 + key_spacing * 15)
            keyboard_x_start = (cam_w - estimated_width) // 2
        if keyboard_y_start is None:
            # 키보드 예상 높이 계산
            estimated_height = int(key_size * 7 + key_spacing * 8)
            keyboard_y_start = (cam_h - estimated_height) // 2 - 50  # 약간 위쪽
        
        self.keyboard_x_start = keyboard_x_start
        self.keyboard_y_start = keyboard_y_start
        self.key_rects = {}
        self._build_keyboard_layout()
        
        # 터치 감지 설정
        self.z_push_threshold = z_push_threshold  # 밀어내는 동작 감지 임계값
        self.z_push_frames_required = 2  # 연속으로 몇 프레임 밀어야 하는지
        self.z_smoothing_alpha = 0.3  # Z축 EMA 평활화
        self.prev_eye_z = None
        self.prev_finger_z = {}
        self.prev_finger_z_raw = {}  # 델타 계산용
        self.finger_push_count = {}  # 각 손가락의 연속 밀기 카운트        
        # 타이핑 상태
        self.typing_enabled = True
        self.show_keyboard = True
        self.show_lines = True
        self.show_z_info = True  # Z축 정보 표시
        self.last_key_press = {}
        self.key_cooldown_ms = 500  # 쿨다운 시간 증가 (밀어내기 동작 간격 확보)
        
        # 시각화
        self.hovered_keys = {}
        self.pressed_keys = {}
        
        # 손바닥 펼침 감지
        self.palm_open_threshold = 3

        if WINDOWS:
            self.SW = win32api.GetSystemMetrics(0)
            self.SH = win32api.GetSystemMetrics(1)
        else:
            self.SW, self.SH = 1920, 1080

    def _build_keyboard_layout(self):
        """텐키리스 키보드 레이아웃 좌표 계산"""
        self.key_rects = {}
        
        x_base = self.keyboard_x_start
        y = self.keyboard_y_start
        
        # Function Keys Row (ESC + F1~F12)
        x = x_base
        for i, key in enumerate(self.KEYBOARD_LAYOUT['row0']):
            if key == 'ESC':
                w = self.key_size
            elif key in ['F1', 'F5', 'F9']:  # 그룹 구분
                w = self.key_size
                if key == 'F1':
                    x += self.key_spacing * 2
                elif key in ['F5', 'F9']:
                    x += self.key_spacing * 2
            else:
                w = self.key_size
            
            self.key_rects[key] = (x, y, w, self.key_size)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing * 3
        
        # Number Row
        x = x_base
        for key in self.KEYBOARD_LAYOUT['row1']:
            if key == 'BKSP':
                w = int(self.key_size * 1.5)
            else:
                w = self.key_size
            
            self.key_rects[key] = (x, y, w, self.key_size)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing
        
        # QWERTY Row
        x = x_base
        for key in self.KEYBOARD_LAYOUT['row2']:
            if key == 'TAB':
                w = int(self.key_size * 1.3)
            elif key == '\\':
                w = int(self.key_size * 1.2)
            else:
                w = self.key_size
            
            self.key_rects[key] = (x, y, w, self.key_size)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing
        
        # ASDF Row
        x = x_base
        for key in self.KEYBOARD_LAYOUT['row3']:
            if key == 'CAPS':
                w = int(self.key_size * 1.5)
            elif key == 'ENTER':
                w = int(self.key_size * 1.7)
            else:
                w = self.key_size
            
            self.key_rects[key] = (x, y, w, self.key_size)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing
        
        # ZXCV Row
        x = x_base
        for i, key in enumerate(self.KEYBOARD_LAYOUT['row4']):
            if key == 'SHIFT':
                if i == 0:  # Left Shift
                    w = int(self.key_size * 1.8)
                else:  # Right Shift
                    w = int(self.key_size * 2.0)
            else:
                w = self.key_size
            
            self.key_rects[key] = (x, y, w, self.key_size)
            x += w + self.key_spacing
        
        y += self.key_size + self.key_spacing
        
        # Bottom Row (Ctrl, Win, Alt, Space, etc.)
        x = x_base
        for key in self.KEYBOARD_LAYOUT['row5']:
            if key == 'SPACE':
                w = int(self.key_size * 5.5)
            elif key in ['CTRL', 'ALT', 'WIN']:
                w = int(self.key_size * 1.2)
            else:
                w = self.key_size
            
            self.key_rects[key] = (x, y, w, self.key_size)
            x += w + self.key_spacing
        
        # Arrow Keys (아래쪽 별도 배치)
        arrow_y = y
        arrow_x = x_base + int(self.key_size * 14)
        
        # UP key (위쪽)
        self.key_rects['UP'] = (arrow_x + self.key_size + self.key_spacing, 
                                arrow_y - self.key_size - self.key_spacing, 
                                self.key_size, self.key_size)
        
        # LEFT, DOWN, RIGHT (아래쪽)
        self.key_rects['LEFT'] = (arrow_x, arrow_y, self.key_size, self.key_size)
        self.key_rects['DOWN'] = (arrow_x + self.key_size + self.key_spacing, arrow_y, 
                                   self.key_size, self.key_size)
        self.key_rects['RIGHT'] = (arrow_x + (self.key_size + self.key_spacing) * 2, arrow_y, 
                                    self.key_size, self.key_size)
        
        # Edit Keys (오른쪽 상단)
        edit_x = x_base + int(self.key_size * 16)
        edit_y = self.keyboard_y_start + self.key_size + self.key_spacing * 4
        
        edit_keys = self.KEYBOARD_LAYOUT['edit']
        for i, key in enumerate(edit_keys[:3]):  # INS, HOME, PGUP
            self.key_rects[key] = (edit_x + (i % 3) * (self.key_size + self.key_spacing), 
                                   edit_y, 
                                   self.key_size, self.key_size)
        
        edit_y += self.key_size + self.key_spacing
        for i, key in enumerate(edit_keys[3:]):  # DEL, END, PGDN
            self.key_rects[key] = (edit_x + (i % 3) * (self.key_size + self.key_spacing), 
                                   edit_y, 
                                   self.key_size, self.key_size)

    def _get_eye_midpoint_with_z(self, face, w, h):
        """양안 중점 계산 (Z 좌표 포함)"""
        lm = face.landmark
        
        # 오른쪽 눈
        r_outer = np.array([lm[self.R_EYE_OUTER].x * w, lm[self.R_EYE_OUTER].y * h])
        r_outer_z = lm[self.R_EYE_OUTER].z * w
        r_inner = np.array([lm[self.R_EYE_INNER].x * w, lm[self.R_EYE_INNER].y * h])
        r_inner_z = lm[self.R_EYE_INNER].z * w
        r_center = 0.5 * (r_outer + r_inner)
        r_center_z = 0.5 * (r_outer_z + r_inner_z)
        
        # 왼쪽 눈
        l_outer = np.array([lm[self.L_EYE_OUTER].x * w, lm[self.L_EYE_OUTER].y * h])
        l_outer_z = lm[self.L_EYE_OUTER].z * w
        l_inner = np.array([lm[self.L_EYE_INNER].x * w, lm[self.L_EYE_INNER].y * h])
        l_inner_z = lm[self.L_EYE_INNER].z * w
        l_center = 0.5 * (l_outer + l_inner)
        l_center_z = 0.5 * (l_outer_z + l_inner_z)
        
        # 양안 중점
        eye_midpoint = 0.5 * (r_center + l_center)
        eye_midpoint_z = 0.5 * (r_center_z + l_center_z)
        
        # Z축 평활화 (EMA)
        if self.prev_eye_z is None:
            self.prev_eye_z = eye_midpoint_z
        else:
            eye_midpoint_z = (self.z_smoothing_alpha * eye_midpoint_z + 
                             (1 - self.z_smoothing_alpha) * self.prev_eye_z)
            self.prev_eye_z = eye_midpoint_z
        
        return eye_midpoint, r_center, l_center, eye_midpoint_z

    def _get_all_fingertips_with_z(self, hand_landmarks_list, w, h):
        """양손의 모든 손가락 끝 좌표 추출 (Z 좌표 포함)"""
        fingertips = []
        
        for hand_idx, hand in enumerate(hand_landmarks_list):
            lm = hand.landmark
            
            for finger_idx, tip_landmark in enumerate(self.FINGER_TIPS):
                tip_x = lm[tip_landmark].x * w
                tip_y = lm[tip_landmark].y * h
                tip_z_raw = lm[tip_landmark].z * w
                
                finger_id = f"hand{hand_idx}_finger{finger_idx}"
                
                # Z축 평활화
                if finger_id not in self.prev_finger_z:
                    self.prev_finger_z[finger_id] = tip_z_raw
                else:
                    tip_z_raw = (self.z_smoothing_alpha * tip_z_raw + 
                                (1 - self.z_smoothing_alpha) * self.prev_finger_z[finger_id])
                    self.prev_finger_z[finger_id] = tip_z_raw
                
                fingertips.append({
                    'id': finger_id,
                    'hand_idx': hand_idx,
                    'finger_idx': finger_idx,
                    'finger_name': self.FINGER_NAMES[finger_idx],
                    'pos': np.array([tip_x, tip_y]),
                    'z': tip_z_raw,
                    'color': self.FINGER_COLORS[finger_idx]
                })
        
        return fingertips

    def _check_key_collision(self, finger_pos, key_char):
        """손가락과 키 충돌 감지"""
        if key_char not in self.key_rects:
            return False
        
        fx, fy = finger_pos
        kx, ky, kw, kh = self.key_rects[key_char]
        
        return (kx <= fx <= kx + kw) and (ky <= fy <= ky + kh)

    def _detect_z_touch(self, eye_z, finger_z, finger_id):
        """Z축 좌표 변화로 밀어내기 동작 감지
        
        손가락을 카메라 방향으로 연속적으로 밀어낼 때만 터치로 인식
        """
        z_diff = abs(eye_z - finger_z)
        
        # 이전 Z 값 가져오기
        if finger_id not in self.prev_finger_z_raw:
            self.prev_finger_z_raw[finger_id] = finger_z
            self.finger_push_count[finger_id] = 0
            return False, z_diff, 0.0
        
        # Z 변화량 계산 (양수 = 카메라 방향으로 이동)
        z_delta = finger_z - self.prev_finger_z_raw[finger_id]
        self.prev_finger_z_raw[finger_id] = finger_z
        
        # 연속 밀기 카운트 업데이트
        if z_delta > self.z_push_threshold:
            # 임계값 이상 밀고 있음
            self.finger_push_count[finger_id] = self.finger_push_count.get(finger_id, 0) + 1
        else:
            # 밀기 중단 또는 반대 방향
            self.finger_push_count[finger_id] = 0
        
        # 터치 판정: 연속적으로 충분히 밀었는지 확인
        is_touch = self.finger_push_count[finger_id] >= self.z_push_frames_required
        
        # 터치 감지 후 카운트 리셋 (중복 입력 방지)
        if is_touch:
            self.finger_push_count[finger_id] = 0
        
        return is_touch, z_diff, z_delta

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

    def _type_key(self, key_char, finger_name):
        """Win32 API를 사용한 실제 키 입력"""
        if not WINDOWS or not self.typing_enabled:
            return
        
        try:
            # 특수 키 매핑
            special_keys = {
                'ESC': win32con.VK_ESCAPE,
                'F1': win32con.VK_F1, 'F2': win32con.VK_F2, 'F3': win32con.VK_F3,
                'F4': win32con.VK_F4, 'F5': win32con.VK_F5, 'F6': win32con.VK_F6,
                'F7': win32con.VK_F7, 'F8': win32con.VK_F8, 'F9': win32con.VK_F9,
                'F10': win32con.VK_F10, 'F11': win32con.VK_F11, 'F12': win32con.VK_F12,
                'TAB': win32con.VK_TAB,
                'CAPS': win32con.VK_CAPITAL,
                'SHIFT': win32con.VK_SHIFT,
                'CTRL': win32con.VK_CONTROL,
                'ALT': win32con.VK_MENU,
                'WIN': win32con.VK_LWIN,
                'SPACE': win32con.VK_SPACE,
                'ENTER': win32con.VK_RETURN,
                'BKSP': win32con.VK_BACK,
                'UP': win32con.VK_UP,
                'DOWN': win32con.VK_DOWN,
                'LEFT': win32con.VK_LEFT,
                'RIGHT': win32con.VK_RIGHT,
                'INS': win32con.VK_INSERT,
                'DEL': win32con.VK_DELETE,
                'HOME': win32con.VK_HOME,
                'END': win32con.VK_END,
                'PGUP': win32con.VK_PRIOR,
                'PGDN': win32con.VK_NEXT,
            }
            
            if key_char in special_keys:
                vk_code = special_keys[key_char]
            elif len(key_char) == 1:
                # 단일 문자
                vk_code = ord(key_char.upper())
            else:
                return
            
            # 키 누름
            win32api.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.01)
            # 키 뗌
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            print(f"[TYPED] {key_char} (by {finger_name})")
            
            # 시각적 피드백
            self.pressed_keys[key_char] = time.time()
            
        except Exception as e:
            print(f"Typing error: {e}")

    def _draw_keyboard(self, frame):
        """화면에 텐키리스 키보드 그리기"""
        if not self.show_keyboard:
            return frame
        
        # 반투명 배경
        overlay = frame.copy()
        cv2.rectangle(overlay, 
                     (0, 0), 
                     (self.frame_w, self.frame_h), 
                     (20, 20, 20), 
                     -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        
        now = time.time()
        
        # 각 키 그리기
        for key_char, (x, y, w, h) in self.key_rects.items():
            # 키 색상 결정
            if key_char in self.pressed_keys and (now - self.pressed_keys[key_char] < 0.2):
                color = self.KEY_COLOR_PRESSED
            elif key_char in self.hovered_keys.values():
                color = self.KEY_COLOR_HOVER
            elif key_char in ['SHIFT', 'CTRL', 'ALT', 'WIN', 'CAPS', 'TAB', 'ENTER', 'BKSP']:
                color = self.KEY_COLOR_SPECIAL
            else:
                color = self.KEY_COLOR_NORMAL
            
            # 키 박스
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (150, 150, 150), 1)
            
            # 키 텍스트
            if key_char in ['SPACE', 'ENTER', 'SHIFT', 'CTRL', 'BKSP', 'TAB', 'CAPS']:
                font_scale = 0.35
            elif key_char.startswith('F') and len(key_char) <= 3:
                font_scale = 0.4
            else:
                font_scale = 0.5
            
            # 텍스트 표시
            if key_char == 'BKSP':
                text = '←'
            elif key_char == 'UP':
                text = '↑'
            elif key_char == 'DOWN':
                text = '↓'
            elif key_char == 'LEFT':
                text = '←'
            elif key_char == 'RIGHT':
                text = '→'
            else:
                text = key_char
            
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)[0]
            text_x = x + (w - text_size[0]) // 2
            text_y = y + (h + text_size[1]) // 2
            cv2.putText(frame, text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.TEXT_COLOR, 1)
        
        return frame

    def process_frame(self, frame):
        """프레임 처리"""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        face_res = self.face_mesh.process(rgb)
        hand_res = self.hands.process(rgb)
        
        hud = []
        eye_midpoint = None
        eye_z = None
        
        # 얼굴 감지 및 양안 중점 (Z 포함)
        if face_res.multi_face_landmarks:
            face = face_res.multi_face_landmarks[0]
            eye_midpoint, r_center, l_center, eye_z = self._get_eye_midpoint_with_z(face, w, h)
            
            # 눈 중심점 표시
            cv2.circle(frame, (int(r_center[0]), int(r_center[1])), 3, (0, 255, 255), -1)
            cv2.circle(frame, (int(l_center[0]), int(l_center[1])), 3, (0, 255, 255), -1)
            
            # 양안 중점 강조
            cv2.circle(frame, (int(eye_midpoint[0]), int(eye_midpoint[1])), 8, (0, 200, 255), -1)
            cv2.circle(frame, (int(eye_midpoint[0]), int(eye_midpoint[1])), 12, (0, 200, 255), 2)
        
        # 손 감지 및 모든 손가락 추적
        self.hovered_keys = {}
        touch_events = []  # 터치 이벤트 기록
        
        if hand_res.multi_hand_landmarks and eye_z is not None:
            # 손 랜드마크 그리기
            for hand in hand_res.multi_hand_landmarks:
                self.drawer.draw_landmarks(
                    frame, 
                    hand, 
                    mp.solutions.hands.HAND_CONNECTIONS,
                    mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                    mp.solutions.drawing_styles.get_default_hand_connections_style()
                )
            
            # 10개 손가락 TIP 추출 (Z 포함)
            fingertips = self._get_all_fingertips_with_z(hand_res.multi_hand_landmarks, w, h)
            
            for finger_data in fingertips:
                pos = finger_data['pos']
                color = finger_data['color']
                finger_id = finger_data['id']
                finger_name = finger_data['finger_name']
                finger_z = finger_data['z']
                
                # 손가락 끝 표시
                cv2.circle(frame, (int(pos[0]), int(pos[1])), 8, color, -1)
                cv2.circle(frame, (int(pos[0]), int(pos[1])), 10, color, 2)
                
                # 양안 중점에서 손가락까지 선
                if eye_midpoint is not None and self.show_lines:
                    cv2.line(frame, 
                            (int(eye_midpoint[0]), int(eye_midpoint[1])),
                            (int(pos[0]), int(pos[1])),
                            color, 2, cv2.LINE_AA)
                
                # Z축 터치 감지
                is_touch, z_diff, z_delta = self._detect_z_touch(eye_z, finger_z, finger_id)
                
                # Z축 정보 표시 (손가락 옆)
                if self.show_z_info:
                    push_count = self.finger_push_count.get(finger_id, 0)
                    z_text = f"Δ:{z_delta:.3f} [{push_count}/{self.z_push_frames_required}]"
                    z_color = (0, 255, 0) if is_touch else (255, 255, 255)
                    cv2.putText(frame, z_text, 
                               (int(pos[0]) + 15, int(pos[1])), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.35, z_color, 1)
                
                # 키 충돌 감지
                for key_char in self.key_rects.keys():
                    if self._check_key_collision(pos, key_char):
                        self.hovered_keys[finger_id] = key_char
                        
                        # 터치 시 키 입력
                        if is_touch and self._can_press_key(key_char):
                            self._type_key(key_char, finger_name)
                            touch_events.append(f"{finger_name}→{key_char}")
                        
                        break
        
        # 키보드 그리기
        frame = self._draw_keyboard(frame)
        
        # HUD 정보
        eye_z_text = f"{eye_z:.2f}" if eye_z is not None else "N/A"
        hud.append("=== TKL KEYBOARD (Z-AXIS TOUCH) ===")
        hud.append(f"Typing: {'ON' if self.typing_enabled else 'OFF'} | Keyboard: {'ON' if self.show_keyboard else 'OFF'}")
        hud.append(f"Face: {'YES' if eye_z is not None else 'NO'} | Eye Z: {eye_z_text}")
        
        if hand_res.multi_hand_landmarks:
            fingertips = self._get_all_fingertips_with_z(hand_res.multi_hand_landmarks, w, h)
            hud.append(f"Hands: {len(hand_res.multi_hand_landmarks)}/2 | Fingers: {len(fingertips)}/10")
        else:
            hud.append(f"Hands: 0/2 | Fingers: 0/10")
        
        hud.append(f"Z Push Threshold: {self.z_push_threshold:.3f} (±/- to adjust)")
        hud.append(f"Required Frames: {self.z_push_frames_required} consecutive pushes")
        
        # 터치 이벤트 표시
        if touch_events:
            hud.append(f"TOUCH: {' | '.join(touch_events)}")
        
        # 호버 중인 키
        if self.hovered_keys:
            hover_text = " | ".join([f"{key}" for key in self.hovered_keys.values()])
            hud.append(f"Hover: {hover_text[:60]}...")
        
        return frame, hud

    def run(self):
        """메인 실행 루프"""
        if not self.cap.isOpened():
            print("Failed to open webcam.")
            return
        
        print("=" * 70)
        print("VIRTUAL TKL KEYBOARD - Z-AXIS TOUCH DETECTION")
        print("=" * 70)
        print("Controls:")
        print("  q: Quit")
        print("  t: Toggle typing ON/OFF")
        print("  k: Toggle keyboard display ON/OFF")
        print("  l: Toggle eye→finger lines ON/OFF")
        print("  z: Toggle Z-axis info ON/OFF")
        print("  +: Increase Z push threshold (need to push harder)")
        print("  -: Decrease Z push threshold (easier to trigger)")
        print("")
        print("How to type:")
        print("  1. Show your face to camera (eyes detected)")
        print("  2. Position finger over a key (XY plane)")
        print("  3. PUSH finger toward camera STRONGLY (Z delta > 0.10)")
        print("  4. Push must be continuous for 2 frames")
        print("  5. Key is typed on successful push!")
        print("")
        print("Tip: Make DELIBERATE pushing motion - not just positioning")
        print("     Watch Δ value increase above threshold!")
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
                    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                    cv2.rectangle(out, (5, y - 20), (15 + text_w, y + 5), (0, 0, 0), -1)
                    
                    # 텍스트
                    if "ON" in text or "YES" in text or "TOUCH:" in text:
                        color = (0, 255, 0)
                    elif "TKL" in text:
                        color = (0, 255, 255)
                    else:
                        color = (200, 200, 200)
                    
                    cv2.putText(out, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    y += 25
                
                cv2.imshow("Virtual TKL Keyboard - Z-Axis Touch", out)
                
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
                elif key == ord('l'):
                    self.show_lines = not self.show_lines
                    print(f"Eye→Finger lines: {'ON' if self.show_lines else 'OFF'}")
                elif key == ord('z'):
                    self.show_z_info = not self.show_z_info
                    print(f"Z-axis info: {'ON' if self.show_z_info else 'OFF'}")
                elif key == ord('+') or key == ord('='):
                    self.z_push_threshold += 0.01
                    print(f"Z push threshold: {self.z_push_threshold:.3f}")
                elif key == ord('-') or key == ord('_'):
                    self.z_push_threshold = max(0.01, self.z_push_threshold - 0.01)
                    print(f"Z push threshold: {self.z_push_threshold:.3f}")
        
        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            print("\nVirtual TKL Keyboard terminated.")


def main():
    app = VirtualKeyboardTKL(
        cam_index=0,
        cam_w=1280,
        cam_h=720,
        det_conf_face=0.5,
        det_conf_hand=0.7,
        track_conf_hand=0.6,
        key_size=35,
        key_spacing=3,
        keyboard_x_start=None,  # 자동 중앙 정렬
        keyboard_y_start=None,  # 자동 중앙 정렬
        z_push_threshold=0.10  # Z축 밀어내기 감지 임계값 (높을수록 강하게 밀어야 함)
    )
    app.run()


if __name__ == "__main__":
    main()