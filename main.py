"""
AirTouch - Virtual Touch Plane V6
Main Application with Mode Switching

손 제스처 기반 마우스 제어 + 가상 키보드 시스템
Shaka 제스처(🤙)로 모드 전환
"""

import cv2
import time
import config
from gesture import FaceDetector, HandDetector, FingerGestureRecognizer, PinchRecognizer, ShakaModeRecognizer
from control import MouseController, ClickManager, CursorMapper, SystemCursorChanger
from control import PinchZoomManager, ZoomGuard, VirtualKeyboard
from state import StateManager, ModeManager
from scroll import ScrollGestureManager


class AirTouchApp:
    """
    AirTouch 메인 애플리케이션 클래스
    - 터치 모드: 기존 마우스 제어
    - 키보드 모드: 가상 키보드
    """

    def __init__(self):
        # 웹캠 초기화
        self.cap = cv2.VideoCapture(config.CAM_INDEX, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)

        # 검출기
        self.face_detector = FaceDetector()
        self.hand_detector = HandDetector()

        # 제스처 인식기
        self.finger_recognizer = FingerGestureRecognizer()
        self.pinch_recognizer = PinchRecognizer()
        self.shaka_recognizer = ShakaModeRecognizer(hold_duration_ms=2000)

        # 상태 관리
        self.state_manager = StateManager()
        self.mode_manager = ModeManager()

        # 마우스 제어 (터치 모드)
        self.mouse_controller = MouseController()
        self.click_manager = ClickManager(
            refractory_ms=config.REFRACTORY_MS,
            double_click_hold_ms=config.DBL_HOLD_MS
        )

        # 커서 제어
        self.cursor_mapper = CursorMapper(
            ema_alpha=config.EMA_CURSOR_ALPHA,
            move_threshold=config.MOVE_THRESHOLD,
            mirror=config.MIRROR_DEFAULT
        )
        self.cursor_on = config.CURSOR_DEFAULT_ON

        self.cursor_changer = SystemCursorChanger(
            enabled=config.CHANGE_CURSOR_ON_ACTIVE,
            active_cursor_shape=config.ACTIVE_CURSOR_SHAPE
        )

        # Zoom 제어
        self.pinch_zoom_manager = PinchZoomManager(
            px_per_step=config.PX_PER_STEP,
            deadzone_px=config.DEADZONE_PX,
            max_steps_per_frame=config.MAX_STEPS_PER_FRAME,
            z_normalization_enabled=config.Z_NORMALIZATION_ENABLED,
            min_z_for_normalization=config.MIN_Z_FOR_NORMALIZATION,
            reference_z_frames=config.REFERENCE_Z_FRAMES,
            ema_alpha=config.EMA_PINCH_ALPHA
        )

        self.zoom_guard = ZoomGuard(
            active_grace_ms=config.ACTIVE_GRACE_MS,
            release_cooldown_ms=config.RELEASE_COOLDOWN_MS,
            edge_band=config.EDGE_BAND,
            drop_guard=config.DROP_GUARD
        )

        # 가상 키보드 (키보드 모드)
        self.virtual_keyboard = VirtualKeyboard(
            frame_width=config.CAM_WIDTH,
            frame_height=config.CAM_HEIGHT,
            key_size=60,
            key_spacing=10,
            keyboard_y_start=400,
            click_angle_threshold=150.0,
            release_angle_threshold=165.0
        )

        # 스크롤 제스처 (터치 모드)
        self.scroll_manager = ScrollGestureManager()

        # Shaka 제스처 진행률 (시각화용)
        self.shaka_progress = 0.0

    def draw_mode_indicator(self, frame):
        """모드 표시"""
        mode = self.mode_manager.get_mode()

        if mode == ModeManager.TOUCH_MODE:
            color = (0, 255, 0)  # 초록색
            text = "MODE: TOUCH"
        else:
            color = (255, 0, 255)  # 자홍색
            text = "MODE: KEYBOARD"

        # 배경
        cv2.rectangle(frame, (10, 10), (300, 60), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (300, 60), color, 3)

        # 텍스트
        cv2.putText(frame, text, (20, 45),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    def draw_shaka_progress(self, frame):
        """Shaka 제스처 진행률 표시"""
        if self.shaka_progress > 0:
            bar_x = 320
            bar_y = 20
            bar_width = 200
            bar_height = 30

            # 배경
            cv2.rectangle(frame, (bar_x, bar_y),
                         (bar_x + bar_width, bar_y + bar_height),
                         (50, 50, 50), -1)
            cv2.rectangle(frame, (bar_x, bar_y),
                         (bar_x + bar_width, bar_y + bar_height),
                         (200, 200, 200), 2)

            # 진행률
            fill_width = int(bar_width * self.shaka_progress)
            if fill_width > 0:
                color = (0, 255, 255) if self.shaka_progress < 1.0 else (0, 255, 0)
                cv2.rectangle(frame, (bar_x, bar_y),
                             (bar_x + fill_width, bar_y + bar_height),
                             color, -1)

            # 텍스트
            text = f"Hold: {int(self.shaka_progress * 100)}%"
            cv2.putText(frame, text, (bar_x + 10, bar_y + 22),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def process_touch_mode(self, frame, eye_mid_z, idx_tip_z, thm_tip_z,
                          landmarks_2d, angles, pinch_distance, shaka_detected=False,
                          hand_landmarks_list=None):
        """터치 모드 처리"""
        hud = []
        now_ms = int(time.time() * 1000)

        # Z 거리 계산 및 상태 판정
        z_distance = abs(eye_mid_z - idx_tip_z)
        state_info = self.state_manager.process_z_distance(z_distance)

        # 상태 전환 처리
        if state_info['state_changed']:
            if state_info['new_state']:  # IDLE → ACTIVE
                self.zoom_guard.set_grace_period(now_ms)
                self.cursor_changer.apply_active_cursor()

                if self.mouse_controller.is_dragging():
                    self.mouse_controller.drag_end()

                self.pinch_zoom_manager.reset()
            else:  # ACTIVE → IDLE
                self.zoom_guard.set_cooldown(now_ms)
                self.cursor_changer.restore_cursor()
                self.pinch_zoom_manager.reset()

        # HUD 업데이트
        hud.append(f"[Z-ONLY] factor:{self.state_manager.factor:.2f} "
                   f"|Δz|:{state_info['z_len_filtered']:.1f} "
                   f"base:{state_info['base_len']:.1f} "
                   f"on:{state_info['threshold_on']:.1f} "
                   f"off:{state_info['threshold_off']:.1f}")
        hud.append("ACTIVE" if state_info['active'] else "IDLE")

        # ACTIVE 상태: Pinch Zoom
        if state_info['active'] and pinch_distance is not None and thm_tip_z is not None:
            steps_to_fire, zoom_info = self.pinch_zoom_manager.process_pinch(
                pinch_distance, idx_tip_z, thm_tip_z
            )

            # Zoom 허용 체크
            allowed, reason = self.zoom_guard.is_zoom_allowed(
                now_ms,
                state_info['z_len_filtered'],
                state_info['threshold_on'],
                state_info['threshold_off']
            )

            if not allowed:
                hud.append(f"ZOOM BLOCKED: {reason}")
            elif steps_to_fire != 0:
                self.pinch_zoom_manager.execute_zoom(steps_to_fire)

        # IDLE 상태: 클릭/드래그 제스처
        if not state_info['active'] and angles is not None:
            if self.cursor_on:
                if shaka_detected:
                    hud.append("(IDLE) cursor only - Shaka blocking clicks/drag")
                else:
                    hud.append("(IDLE) cursor + clicks/drag enabled")

            # Shaka 제스처 중에는 클릭/드래그 차단
            if not shaka_detected:
                # 클릭 (검지)
                if self.finger_recognizer.is_click_triggered(angles['idx']):
                    if self.click_manager.can_click(now_ms):
                        self.mouse_controller.click()
                        self.click_manager.register_click(now_ms)

                # 드래그 (중지)
                if self.finger_recognizer.is_drag_triggered(angles['mid']):
                    if not self.mouse_controller.is_dragging():
                        self.mouse_controller.drag_start()
                else:
                    if self.finger_recognizer.is_drag_released(angles['mid']):
                        if self.mouse_controller.is_dragging():
                            self.mouse_controller.drag_end()
            else:
                # Shaka 제스처 중 드래그 중이었다면 종료
                if self.mouse_controller.is_dragging():
                    self.mouse_controller.drag_end()

        # 스크롤 제스처 처리 (양손 Pinch)
        if hand_landmarks_list:
            h, w = frame.shape[:2]
            scroll_status = self.scroll_manager.process_dual_hand_scroll(
                hand_landmarks_list, self.hand_detector, w, h
            )
            if scroll_status:
                hud.append(f"Scroll: {scroll_status}")

        return frame, hud

    def process_keyboard_mode(self, frame, eye_midpoint, landmarks_2d):
        """키보드 모드 처리"""
        hud = []

        # 가상 키보드 처리
        frame = self.virtual_keyboard.process_keyboard_frame(
            frame, eye_midpoint, landmarks_2d
        )

        # 키보드 HUD 정보
        keyboard_info = self.virtual_keyboard.get_hud_info()
        hud.extend(keyboard_info)

        return frame, hud

    def process_frame(self, frame):
        """
        프레임 처리 메인 로직

        Args:
            frame: 웹캠 프레임 (BGR)

        Returns:
            (output_frame, hud_lines)
        """
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        hud = []

        # 얼굴 검출
        face_landmarks = self.face_detector.detect(rgb)
        eye_mid_xy = None
        eye_mid_z = None

        if face_landmarks:
            r_eye_xy, l_eye_xy, eye_mid_xy, eye_mid_z = \
                self.face_detector.get_eye_midpoint(face_landmarks, w, h)

            # 시각화
            cv2.circle(frame, (int(eye_mid_xy[0]), int(eye_mid_xy[1])), 8, (0, 200, 255), -1)

        # 손 검출 (복수 손 처리)
        hand_landmarks_list = self.hand_detector.detect(rgb)
        idx_tip_z = None
        thm_tip_z = None
        normalized_landmarks = None
        landmarks_2d = None
        angles = None
        pinch_distance = None
        shaka_detected = False  # Shaka 제스처 감지 플래그

        if hand_landmarks_list:
            # 모든 손 검출하여 Shaka 제스처 확인
            for hand_landmarks in hand_landmarks_list:
                temp_landmarks_2d = self.hand_detector.get_landmarks_2d(hand_landmarks, w, h)
                if self.shaka_recognizer.is_shaka_gesture(temp_landmarks_2d):
                    shaka_detected = True
                    break

            # 첫 번째 손을 제어용으로 사용 (기존 로직 유지)
            control_hand = hand_landmarks_list[0]

            # 랜드마크 그리기
            for hand_landmarks in hand_landmarks_list:
                self.hand_detector.draw_landmarks(frame, hand_landmarks)

            # 2D 랜드마크
            landmarks_2d = self.hand_detector.get_landmarks_2d(control_hand, w, h)

            # 3D 랜드마크 (Z 좌표)
            landmarks_3d = self.hand_detector.get_landmarks_3d(control_hand, w)
            idx_tip_z = landmarks_3d['idx_tip_z']
            thm_tip_z = landmarks_3d['thm_tip_z']

            # 정규화된 좌표 (커서 매핑용)
            normalized_landmarks = self.hand_detector.get_normalized_landmarks(control_hand)

            # 손가락 각도 계산
            angles = self.finger_recognizer.calculate_finger_angles(landmarks_2d)

            # Pinch 거리 계산
            pinch_distance = self.pinch_recognizer.calculate_pinch_distance(landmarks_2d)

            # Shaka 제스처 감지 (모드 전환)
            now_ms = int(time.time() * 1000)
            mode_changed, self.shaka_progress = self.shaka_recognizer.check_hold_duration(
                shaka_detected, now_ms
            )

            if mode_changed:
                self.mode_manager.toggle_mode()
        else:
            self.shaka_progress = 0.0
            shaka_detected = False

        # 커서 매핑 (터치 모드에서만)
        if self.mode_manager.is_touch_mode():
            if self.cursor_on and normalized_landmarks:
                anchor_x = 0.5 * normalized_landmarks['idx_mcp'][0] + 0.5 * normalized_landmarks['mid_mcp'][0]
                anchor_y = 0.5 * normalized_landmarks['idx_mcp'][1] + 0.5 * normalized_landmarks['mid_mcp'][1]
                screen_x, screen_y, moved = self.cursor_mapper.map_to_screen(anchor_x, anchor_y)

                if moved:
                    self.mouse_controller.set_cursor_position(screen_x, screen_y)

        # 필수 신호 확인
        if eye_mid_z is None or idx_tip_z is None or landmarks_2d is None:
            # 손이나 얼굴이 안 보임
            if self.mouse_controller.is_dragging():
                self.mouse_controller.drag_end()

            if self.state_manager.is_active():
                self.cursor_changer.restore_cursor()

            self.pinch_zoom_manager.reset()
            self.zoom_guard.reset()

            hud.append("Status: IDLE (need face + hand)")
            return frame, hud

        # 모드별 처리
        if self.mode_manager.is_touch_mode():
            frame, mode_hud = self.process_touch_mode(
                frame, eye_mid_z, idx_tip_z, thm_tip_z,
                landmarks_2d, angles, pinch_distance, shaka_detected,
                hand_landmarks_list
            )
            hud.extend(mode_hud)
        else:  # KEYBOARD_MODE
            frame, mode_hud = self.process_keyboard_mode(
                frame, eye_mid_xy, landmarks_2d
            )
            hud.extend(mode_hud)

        return frame, hud

    def draw_hud(self, frame, hud_lines):
        """
        HUD 그리기

        Args:
            frame: 프레임
            hud_lines: HUD 텍스트 리스트
        """
        y = config.HUD_START_Y + 70  # 모드 표시 아래부터
        for line in hud_lines:
            color = config.HUD_COLOR_ACTIVE if "ACTIVE" in line else config.HUD_COLOR_NORMAL
            cv2.putText(frame, line, (10, y), config.HUD_FONT,
                       config.HUD_FONT_SCALE, color, config.HUD_FONT_THICKNESS, cv2.LINE_AA)
            y += config.HUD_LINE_HEIGHT

    def handle_key(self, key):
        """
        키보드 입력 처리

        Args:
            key: 키 코드

        Returns:
            True: 계속 실행, False: 종료
        """
        if key == ord('q'):
            return False
        elif key == ord('c'):
            self.cursor_on = not self.cursor_on
        elif key == ord('m'):
            self.cursor_mapper.toggle_mirror()
        elif key == ord('n'):
            enabled = self.pinch_zoom_manager.toggle_normalization()
            print(f"\n원근 보정: {'ON' if enabled else 'OFF'}")
        elif key == ord('<'):
            factor = self.state_manager.decrease_factor()
            print(f"\nFactor: {factor:.2f}")
        elif key == ord('>'):
            factor = self.state_manager.increase_factor()
            print(f"\nFactor: {factor:.2f}")
        elif key == ord('r'):
            self.state_manager.reset_baseline()
            print("\nBaseline reset!")
        elif key == ord('t'):
            # 키보드 모드에서만 작동
            if self.mode_manager.is_keyboard_mode():
                enabled = self.virtual_keyboard.toggle_typing()
                print(f"\nTyping: {'ON' if enabled else 'OFF'}")
        elif key == ord('k'):
            # 키보드 모드에서만 작동
            if self.mode_manager.is_keyboard_mode():
                enabled = self.virtual_keyboard.toggle_keyboard_display()
                print(f"\nKeyboard Display: {'ON' if enabled else 'OFF'}")

        return True

    def run(self):
        """메인 루프"""
        if not self.cap.isOpened():
            print("Failed to open webcam.")
            return

        print("=" * 70)
        print("AirTouch V6 - Touch & Keyboard Mode")
        print("=" * 70)
        print("Controls:")
        print("  q: Quit")
        print("  Shaka Gesture (hold 2s): Toggle Touch <-> Keyboard Mode")
        print("")
        print("Touch Mode:")
        print("  c: Toggle cursor ON/OFF")
        print("  m: Mirror cursor")
        print("  n: Toggle perspective correction")
        print("  r: Reset baseline")
        print("")
        print("Keyboard Mode:")
        print("  t: Toggle typing ON/OFF")
        print("  k: Toggle keyboard display")
        print("=" * 70)

        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break

                # 좌우 반전 (거울 모드)
                frame = cv2.flip(frame, 1)

                # 프레임 처리
                output, hud = self.process_frame(frame)

                # 모드 표시
                self.draw_mode_indicator(output)

                # Shaka 진행률 표시
                self.draw_shaka_progress(output)

                # HUD 그리기
                self.draw_hud(output, hud)

                # 화면 표시
                cv2.imshow(config.WINDOW_NAME, output)

                # 키 입력 처리
                key = cv2.waitKey(1) & 0xFF
                if key != 255:  # 키 입력이 있을 때
                    if not self.handle_key(key):
                        break

        finally:
            self.cleanup()

    def cleanup(self):
        """리소스 정리"""
        print("\nCleaning up...")

        # 마우스 상태 정리
        self.mouse_controller.force_release()

        # 커서 복원
        self.cursor_changer.restore_cursor()

        # 웹캠 해제
        self.cap.release()

        # MediaPipe 리소스 해제
        self.face_detector.close()
        self.hand_detector.close()

        # 창 닫기
        cv2.destroyAllWindows()

        print("Cleanup complete.")


def main():
    """진입점"""
    app = AirTouchApp()
    app.run()


if __name__ == "__main__":
    main()
