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


class VirtualKeyboardWithHandTracking:
    """
    가상 키보드: 양손 손바닥이 카메라를 향해 펼쳐진 상태에서
    양안의 중점과 10개 손가락 TIP을 선으로 연결하여 HUD에 표시
    """
    # Face mesh landmarks for eyes
    R_EYE_OUTER = 33
    R_EYE_INNER = 133
    L_EYE_OUTER = 263
    L_EYE_INNER = 362
    
    # Hand landmarks for finger tips
    FINGER_TIPS = [
        mp.solutions.hands.HandLandmark.THUMB_TIP,        # 4
        mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP,  # 8
        mp.solutions.hands.HandLandmark.MIDDLE_FINGER_TIP, # 12
        mp.solutions.hands.HandLandmark.RING_FINGER_TIP,   # 16
        mp.solutions.hands.HandLandmark.PINKY_TIP          # 20
    ]

    def __init__(self,
                 cam_index=0, 
                 cam_w=1280, 
                 cam_h=720,
                 det_conf_face=0.5,
                 det_conf_hand=0.7, 
                 track_conf_hand=0.6):
        
        # 카메라 설정
        self.cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_h)

        # MediaPipe Face Mesh 초기화
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=det_conf_face,
            min_tracking_confidence=0.5
        )
        
        # MediaPipe Hands 초기화 (양손 감지를 위해 max_num_hands=2)
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # 양손 감지
            min_detection_confidence=det_conf_hand,
            min_tracking_confidence=track_conf_hand
        )
        
        self.drawer = mp.solutions.drawing_utils
        
        # 키보드 모드 토글
        self.keyboard_mode = True
        
        # 선 색상 설정 (손가락별로 다른 색상)
        self.finger_colors = [
            (255, 0, 0),    # 엄지 - 파란색
            (0, 255, 0),    # 검지 - 초록색
            (0, 255, 255),  # 중지 - 노란색
            (255, 0, 255),  # 약지 - 자홍색
            (255, 128, 0)   # 새끼 - 주황색
        ]

        if WINDOWS:
            self.SW = win32api.GetSystemMetrics(0)
            self.SH = win32api.GetSystemMetrics(1)
        else:
            self.SW, self.SH = 1920, 1080

    def _get_eye_midpoint(self, face, w, h):
        """양안의 중점 계산"""
        lm = face.landmark
        
        # 오른쪽 눈 중심
        r_outer = np.array([lm[self.R_EYE_OUTER].x * w, lm[self.R_EYE_OUTER].y * h])
        r_inner = np.array([lm[self.R_EYE_INNER].x * w, lm[self.R_EYE_INNER].y * h])
        r_center = 0.5 * (r_outer + r_inner)
        
        # 왼쪽 눈 중심
        l_outer = np.array([lm[self.L_EYE_OUTER].x * w, lm[self.L_EYE_OUTER].y * h])
        l_inner = np.array([lm[self.L_EYE_INNER].x * w, lm[self.L_EYE_INNER].y * h])
        l_center = 0.5 * (l_outer + l_inner)
        
        # 양안의 중점
        eye_midpoint = 0.5 * (r_center + l_center)
        
        return eye_midpoint, r_center, l_center

    def _get_finger_tips(self, hand, w, h):
        """손의 모든 손가락 TIP 좌표 추출"""
        lm = hand.landmark
        tips = []
        
        for tip_landmark in self.FINGER_TIPS:
            tip_x = lm[tip_landmark].x * w
            tip_y = lm[tip_landmark].y * h
            tips.append(np.array([tip_x, tip_y]))
        
        return tips

    def _is_palm_open(self, hand):
        """손바닥이 펼쳐져 있는지 확인 (간단한 휴리스틱)"""
        lm = hand.landmark
        
        # 손가락이 펼쳐져 있는지 확인 (TIP이 MCP보다 위에 있는지)
        # 엄지는 제외하고 나머지 4개 손가락만 체크
        fingers_extended = 0
        
        # 검지
        if lm[8].y < lm[6].y:  # INDEX_TIP < INDEX_MCP
            fingers_extended += 1
        # 중지
        if lm[12].y < lm[10].y:  # MIDDLE_TIP < MIDDLE_MCP
            fingers_extended += 1
        # 약지
        if lm[16].y < lm[14].y:  # RING_TIP < RING_MCP
            fingers_extended += 1
        # 새끼
        if lm[20].y < lm[18].y:  # PINKY_TIP < PINKY_MCP
            fingers_extended += 1
        
        # 4개 손가락 중 3개 이상이 펼쳐져 있으면 손바닥이 펼쳐진 것으로 판단
        return fingers_extended >= 3

    def process_frame(self, frame):
        """프레임 처리 및 시각화"""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # MediaPipe 처리
        face_res = self.face_mesh.process(rgb)
        hand_res = self.hands.process(rgb)
        
        hud = []
        eye_midpoint = None
        all_finger_tips = []
        hands_detected = 0
        palms_open = 0

        # === 얼굴 인식 및 양안 중점 추출 ===
        if face_res.multi_face_landmarks:
            face = face_res.multi_face_landmarks[0]
            eye_midpoint, r_center, l_center = self._get_eye_midpoint(face, w, h)
            
            # 눈 중심점들 표시
            cv2.circle(frame, (int(r_center[0]), int(r_center[1])), 3, (0, 255, 255), -1)
            cv2.circle(frame, (int(l_center[0]), int(l_center[1])), 3, (0, 255, 255), -1)
            
            # 양안 중점 강조 표시 (큰 원)
            cv2.circle(frame, (int(eye_midpoint[0]), int(eye_midpoint[1])), 8, (0, 200, 255), -1)
            cv2.circle(frame, (int(eye_midpoint[0]), int(eye_midpoint[1])), 12, (0, 200, 255), 2)

        # === 양손 인식 및 손가락 TIP 추출 ===
        if hand_res.multi_hand_landmarks:
            hands_detected = len(hand_res.multi_hand_landmarks)
            
            for hand_idx, hand in enumerate(hand_res.multi_hand_landmarks):
                # 손 랜드마크 그리기
                self.drawer.draw_landmarks(
                    frame, 
                    hand, 
                    mp.solutions.hands.HAND_CONNECTIONS,
                    mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                    mp.solutions.drawing_styles.get_default_hand_connections_style()
                )
                
                # 손바닥이 펼쳐져 있는지 확인
                is_open = self._is_palm_open(hand)
                if is_open:
                    palms_open += 1
                
                # 손가락 TIP 좌표 추출
                finger_tips = self._get_finger_tips(hand, w, h)
                
                # 각 손가락 TIP 표시 및 저장
                for tip_idx, tip_pos in enumerate(finger_tips):
                    color = self.finger_colors[tip_idx]
                    cv2.circle(frame, (int(tip_pos[0]), int(tip_pos[1])), 6, color, -1)
                    cv2.circle(frame, (int(tip_pos[0]), int(tip_pos[1])), 8, color, 2)
                    
                    all_finger_tips.append({
                        'pos': tip_pos,
                        'color': color,
                        'hand': hand_idx,
                        'finger': tip_idx,
                        'is_open': is_open
                    })

        # === 양안 중점에서 손가락 TIP으로 선 연결 ===
        if eye_midpoint is not None and len(all_finger_tips) > 0:
            for tip_data in all_finger_tips:
                tip_pos = tip_data['pos']
                color = tip_data['color']
                is_open = tip_data['is_open']
                
                # 손바닥이 펼쳐져 있을 때만 선을 그림
                if is_open:
                    # 선 그리기 (굵기 2, 약간 투명한 효과를 위해 밝은 색상 사용)
                    cv2.line(
                        frame,
                        (int(eye_midpoint[0]), int(eye_midpoint[1])),
                        (int(tip_pos[0]), int(tip_pos[1])),
                        color,
                        2,
                        cv2.LINE_AA
                    )
                    
                    # 선의 중점에 작은 원 표시 (시각적 효과)
                    mid_x = int((eye_midpoint[0] + tip_pos[0]) / 2)
                    mid_y = int((eye_midpoint[1] + tip_pos[1]) / 2)
                    cv2.circle(frame, (mid_x, mid_y), 3, color, -1)

        # === HUD 정보 ===
        hud.append(f"=== VIRTUAL KEYBOARD MODE ===")
        hud.append(f"Face Detected: {'YES' if eye_midpoint is not None else 'NO'}")
        hud.append(f"Hands Detected: {hands_detected}/2")
        hud.append(f"Palms Open: {palms_open}/{hands_detected if hands_detected > 0 else 0}")
        hud.append(f"Finger Tips Tracked: {len(all_finger_tips)}/10")
        
        if eye_midpoint is not None:
            hud.append(f"Eye Midpoint: ({int(eye_midpoint[0])}, {int(eye_midpoint[1])})")
        
        # 손가락별 색상 범례
        hud.append("")
        hud.append("Finger Colors:")
        finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        for i, name in enumerate(finger_names):
            hud.append(f"  {name}: RGB{self.finger_colors[i]}")

        return frame, hud

    def run(self):
        """메인 실행 루프"""
        if not self.cap.isOpened():
            print("Failed to open webcam.")
            return
        
        print("=" * 60)
        print("VIRTUAL KEYBOARD - Hand Tracking Mode")
        print("=" * 60)
        print("Controls:")
        print("  q: Quit")
        print("  k: Toggle keyboard mode ON/OFF")
        print("")
        print("Instructions:")
        print("  1. Face the camera with your face visible")
        print("  2. Hold both hands up with palms open facing the camera")
        print("  3. Lines will connect from eye midpoint to all 10 fingertips")
        print("=" * 60)
        
        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break
                
                # 좌우 반전
                frame = cv2.flip(frame, 1)
                
                if self.keyboard_mode:
                    out, hud = self.process_frame(frame)
                    
                    # HUD 텍스트 표시
                    y = 30
                    for text in hud:
                        # 배경 박스 (가독성 향상)
                        (text_w, text_h), _ = cv2.getTextSize(
                            text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                        )
                        cv2.rectangle(
                            out, 
                            (5, y - 22), 
                            (15 + text_w, y + 5), 
                            (0, 0, 0), 
                            -1
                        )
                        
                        # 텍스트
                        color = (0, 255, 0) if "YES" in text or "VIRTUAL" in text else (255, 255, 255)
                        cv2.putText(
                            out, 
                            text, 
                            (10, y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.6, 
                            color, 
                            2, 
                            cv2.LINE_AA
                        )
                        y += 28
                else:
                    out = frame
                    cv2.putText(
                        out, 
                        "Keyboard Mode: OFF (press 'k' to enable)", 
                        (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.8, 
                        (0, 0, 255), 
                        2, 
                        cv2.LINE_AA
                    )
                
                cv2.imshow("Virtual Keyboard - Hand Tracking", out)
                
                # 키 입력 처리
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('k'):
                    self.keyboard_mode = not self.keyboard_mode
                    print(f"Keyboard mode: {'ON' if self.keyboard_mode else 'OFF'}")
        
        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            print("\nVirtual Keyboard terminated.")


def main():
    app = VirtualKeyboardWithHandTracking(
        cam_index=0,
        cam_w=1280,
        cam_h=720,
        det_conf_face=0.5,
        det_conf_hand=0.7,
        track_conf_hand=0.6
    )
    app.run()


if __name__ == "__main__":
    main()