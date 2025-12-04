"""
Shaka 제스처 인식 테스트
엄지+새끼 제스처로 모드 전환 테스트
"""

import cv2
import time
from gesture import FaceDetector, HandDetector, ShakaModeRecognizer
import config


class ShakaGestureTest:
    """Shaka 제스처 테스트 애플리케이션"""

    def __init__(self):
        # 웹캠 초기화
        self.cap = cv2.VideoCapture(config.CAM_INDEX, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)

        # 검출기
        self.hand_detector = HandDetector()

        # Shaka 제스처 인식기
        self.shaka_recognizer = ShakaModeRecognizer(hold_duration_ms=2000)

        # 모드 상태 (시뮬레이션)
        self.current_mode = "TOUCH"
        self.mode_colors = {
            "TOUCH": (0, 255, 0),      # 초록색
            "KEYBOARD": (255, 0, 255)   # 자홍색
        }

    def draw_progress_bar(self, frame, progress):
        """제스처 진행률 표시"""
        bar_x = 50
        bar_y = 100
        bar_width = 300
        bar_height = 30

        # 배경
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     (50, 50, 50), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     (200, 200, 200), 2)

        # 진행률
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            color = (0, 255, 255) if progress < 1.0 else (0, 255, 0)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height),
                         color, -1)

        # 텍스트
        text = f"Hold Progress: {int(progress * 100)}%"
        cv2.putText(frame, text, (bar_x, bar_y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    def draw_finger_angles(self, frame, landmarks_2d, x_offset=50, y_offset=200):
        """각 손가락의 각도 표시"""
        from utils.math_utils import angle_at_joint

        # 엄지
        thumb_angle = angle_at_joint(
            landmarks_2d['thm_cmc'],
            landmarks_2d['thm_mcp'],
            landmarks_2d['thm_ip']
        )

        # 검지
        index_angle = angle_at_joint(
            landmarks_2d['idx_mcp'],
            landmarks_2d['idx_pip'],
            landmarks_2d['idx_dip']
        )

        # 중지
        middle_angle = angle_at_joint(
            landmarks_2d['mid_mcp'],
            landmarks_2d['mid_pip'],
            landmarks_2d['mid_dip']
        )

        # 약지
        ring_angle = angle_at_joint(
            landmarks_2d['ring_mcp'],
            landmarks_2d['ring_pip'],
            landmarks_2d['ring_dip']
        )

        # 새끼
        pinky_angle = angle_at_joint(
            landmarks_2d['pinky_mcp'],
            landmarks_2d['pinky_pip'],
            landmarks_2d['pinky_dip']
        )

        # 각도 표시
        y = y_offset
        line_height = 30

        angles = [
            ("Thumb", thumb_angle, thumb_angle > 150),
            ("Index", index_angle, index_angle < 140),
            ("Middle", middle_angle, middle_angle < 140),
            ("Ring", ring_angle, ring_angle < 140),
            ("Pinky", pinky_angle, pinky_angle > 150)
        ]

        for finger_name, angle, is_correct in angles:
            text = f"{finger_name}: {angle:.1f}°"
            color = (0, 255, 0) if is_correct else (100, 100, 100)

            # 배경
            cv2.rectangle(frame, (x_offset - 5, y - 22),
                         (x_offset + 200, y + 5), (0, 0, 0), -1)

            # 텍스트
            cv2.putText(frame, text, (x_offset, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # 체크 표시
            if is_correct:
                cv2.putText(frame, "✓", (x_offset + 210, y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            y += line_height

    def process_frame(self, frame):
        """프레임 처리"""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 손 검출
        hand_landmarks = self.hand_detector.detect(rgb)

        hud = []
        is_shaka = False
        progress = 0.0
        mode_changed = False

        if hand_landmarks:
            # 손 랜드마크 그리기
            self.hand_detector.draw_landmarks(frame, hand_landmarks)

            # 2D 랜드마크 추출
            landmarks_2d = self.hand_detector.get_landmarks_2d(hand_landmarks, w, h)

            # Shaka 제스처 인식
            is_shaka = self.shaka_recognizer.is_shaka_gesture(landmarks_2d)

            # 2초 홀드 체크
            now_ms = int(time.time() * 1000)
            mode_changed, progress = self.shaka_recognizer.check_hold_duration(is_shaka, now_ms)

            # 모드 전환
            if mode_changed:
                self.current_mode = "KEYBOARD" if self.current_mode == "TOUCH" else "TOUCH"
                print(f"\n>> MODE CHANGED -> {self.current_mode}")

            # 손가락 각도 표시
            if is_shaka:
                self.draw_finger_angles(frame, landmarks_2d)

        # 진행률 바 표시
        if progress > 0:
            self.draw_progress_bar(frame, progress)

        # 현재 모드 표시
        mode_color = self.mode_colors[self.current_mode]
        cv2.rectangle(frame, (10, 10), (400, 80), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (400, 80), mode_color, 3)

        mode_text = f"CURRENT MODE: {self.current_mode}"
        cv2.putText(frame, mode_text, (20, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, mode_color, 3)

        # HUD 정보
        hud.append("=== SHAKA GESTURE TEST ===")
        hud.append(f"Hand Detected: {'YES' if hand_landmarks else 'NO'}")
        hud.append(f"Shaka Gesture: {'YES [OK]' if is_shaka else 'NO'}")
        hud.append(f"Hold Progress: {int(progress * 100)}%")

        if is_shaka:
            hud.append(">> Keep holding for 2 seconds to toggle mode!")

        return frame, hud

    def run(self):
        """메인 루프"""
        if not self.cap.isOpened():
            print("Failed to open webcam.")
            return

        print("=" * 70)
        print("SHAKA GESTURE TEST")
        print("=" * 70)
        print("How to test:")
        print("  1. Show your hand to the camera")
        print("  2. Make 'Shaka' gesture (hang loose)")
        print("     - Thumb extended")
        print("     - Index, Middle, Ring curled")
        print("     - Pinky extended")
        print("  3. Hold for 2 seconds")
        print("  4. Mode will toggle between TOUCH <-> KEYBOARD")
        print("")
        print("Controls:")
        print("  q: Quit")
        print("=" * 70)

        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break

                # 좌우 반전
                frame = cv2.flip(frame, 1)

                # 프레임 처리
                output, hud = self.process_frame(frame)

                # HUD 그리기
                y = 550
                for text in hud:
                    # 배경
                    (text_w, text_h), _ = cv2.getTextSize(
                        text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
                    )
                    cv2.rectangle(output, (5, y - 22), (15 + text_w, y + 5), (0, 0, 0), -1)

                    # 텍스트
                    color = (0, 255, 0) if "YES" in text else (255, 255, 255)
                    cv2.putText(output, text, (10, y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    y += 30

                # 화면 표시
                cv2.imshow("Shaka Gesture Test", output)

                # 키 입력
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break

        finally:
            self.cap.release()
            self.hand_detector.close()
            cv2.destroyAllWindows()
            print("\nTest completed.")


def main():
    app = ShakaGestureTest()
    app.run()


if __name__ == "__main__":
    main()
