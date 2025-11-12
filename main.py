"""
AirTouch - Virtual Touch Plane V5
Main Application

손 제스처 기반 마우스 제어 시스템
"""

import cv2
import time
import config
from gesture import FaceDetector, HandDetector, FingerGestureRecognizer, PinchRecognizer
from control import MouseController, ClickManager, CursorMapper, SystemCursorChanger
from control import PinchZoomManager, ZoomGuard
from state import StateManager


class AirTouchApp:
    """
    AirTouch 메인 애플리케이션 클래스
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
        
        # 상태 관리
        self.state_manager = StateManager()
        
        # 마우스 제어
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
            for point, color in [(r_eye_xy, (0,255,255)), (l_eye_xy, (0,255,255)), (eye_mid_xy, (0,200,255))]:
                cv2.circle(frame, (int(point[0]), int(point[1])), 3, color, -1)
        
        # 손 검출
        hand_landmarks = self.hand_detector.detect(rgb)
        idx_tip_z = None
        thm_tip_z = None
        normalized_landmarks = None
        landmarks_2d = None
        angles = None
        pinch_distance = None
        
        if hand_landmarks:
            # 랜드마크 그리기
            self.hand_detector.draw_landmarks(frame, hand_landmarks)
            
            # 2D 랜드마크
            landmarks_2d = self.hand_detector.get_landmarks_2d(hand_landmarks, w, h)
            
            # 3D 랜드마크 (Z 좌표)
            landmarks_3d = self.hand_detector.get_landmarks_3d(hand_landmarks, w)
            idx_tip_z = landmarks_3d['idx_tip_z']
            thm_tip_z = landmarks_3d['thm_tip_z']
            
            # 정규화된 좌표 (커서 매핑용)
            normalized_landmarks = self.hand_detector.get_normalized_landmarks(hand_landmarks)
            
            # 시각화: 커서 앵커 포인트
            anchor_px = 0.5 * (landmarks_2d['idx_mcp'] + landmarks_2d['mid_mcp'])
            cv2.circle(frame, (int(anchor_px[0]), int(anchor_px[1])), 5, (255, 0, 255), -1)
            
            # 시각화: 양안 중점 ↔ 검지 TIP 연결선
            if eye_mid_xy is not None:
                cv2.line(frame, 
                        (int(eye_mid_xy[0]), int(eye_mid_xy[1])),
                        (int(landmarks_2d['idx_tip'][0]), int(landmarks_2d['idx_tip'][1])),
                        (0, 255, 0), 2)
            
            # 손가락 각도 계산
            angles = self.finger_recognizer.calculate_finger_angles(landmarks_2d)
            
            # Pinch 거리 계산
            pinch_distance = self.pinch_recognizer.calculate_pinch_distance(landmarks_2d)
        
        # 커서 매핑
        if self.cursor_on and normalized_landmarks:
            anchor_x = 0.5 * normalized_landmarks['idx_mcp'][0] + 0.5 * normalized_landmarks['mid_mcp'][0]
            anchor_y = 0.5 * normalized_landmarks['idx_mcp'][1] + 0.5 * normalized_landmarks['mid_mcp'][1]
            screen_x, screen_y, moved = self.cursor_mapper.map_to_screen(anchor_x, anchor_y)
            
            if moved:
                self.mouse_controller.set_cursor_position(screen_x, screen_y)
            
            hud.append(f"CURSOR: ON | anchor=AVG(INDEX_MCP, MIDDLE_MCP) | mirror={'ON' if self.cursor_mapper.mirror else 'OFF'}")
        else:
            hud.append("CURSOR: OFF (press 'c')")
        
        # 필수 신호 확인
        if eye_mid_z is None or idx_tip_z is None:
            # 손이나 얼굴이 안 보임
            if self.mouse_controller.is_dragging():
                self.mouse_controller.drag_end()
            
            if self.state_manager.is_active():
                self.cursor_changer.restore_cursor()
            
            self.pinch_zoom_manager.reset()
            self.zoom_guard.reset()
            
            hud.append("Status: IDLE (need face + hand z)")
            return frame, hud
        
        # Z 거리 계산 및 상태 판정
        z_distance = abs(eye_mid_z - idx_tip_z)
        state_info = self.state_manager.process_z_distance(z_distance)
        
        # 상태 전환 처리
        now_ms = int(time.time() * 1000)
        
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
                   f"off:{state_info['threshold_off']:.1f} "
                   f"z_margin:{self.state_manager.z_margin:.1f} "
                   f"hyst:{self.state_manager.hysteresis_ratio:.2f}")
        hud.append(f"z_mid:{eye_mid_z:.1f}  z_tip:{idx_tip_z:.1f}")
        hud.append("ACTIVE" if state_info['active'] else "IDLE")
        hud.append(f"Perspective Correction: {'ON' if self.pinch_zoom_manager.z_normalization_enabled else 'OFF'} (press 'n' to toggle)")
        hud.append("press 'r' to reset baseline")
        
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
            
            # HUD 추가
            if zoom_info['collecting_ref_z']:
                hud.append(f"Collecting reference Z: {len(self.pinch_zoom_manager._z_samples)}/{self.pinch_zoom_manager.reference_z_frames}")
            elif zoom_info['reference_z'] is not None:
                hud.append(f"z_avg:{zoom_info.get('z_avg', 0):.1f} ref_z:{zoom_info['reference_z']:.1f} scale:{zoom_info['z_scale_factor']:.3f}")
            
            if zoom_info['base_pinch'] is not None:
                hud.append(f"pinch_raw:{zoom_info['raw_pinch']:.1f} normalized:{zoom_info['normalized_pinch']:.1f} base:{zoom_info['base_pinch']:.1f}")
                hud.append(f"Δ:{zoom_info['delta']:.1f} total_steps:{zoom_info['steps_total']} "
                           f"fired:{0 if not allowed else zoom_info['steps_to_fire']} "
                           f"(px/step {self.pinch_zoom_manager.px_per_step}, dz {self.pinch_zoom_manager.deadzone_px})")
            else:
                hud.append(f"pinch:{zoom_info['normalized_pinch']:.1f} (waiting for reference Z or base)")
        
        # IDLE 상태: 클릭/드래그 제스처
        if not state_info['active'] and angles is not None:
            if self.cursor_on:
                hud.append("(IDLE) cursor only – clicks/drag enabled")
            
            # 클릭 (검지)
            if self.finger_recognizer.is_click_triggered(angles['idx']):
                if self.click_manager.can_click(now_ms):
                    self.mouse_controller.click()
                    self.click_manager.register_click(now_ms)
            
            # 더블클릭 (검지 홀드)
            if self.finger_recognizer.is_click_triggered(angles['idx']):
                self.click_manager.start_double_click_hold(now_ms)
                if self.click_manager.check_double_click_hold(now_ms):
                    self.mouse_controller.double_click()
            else:
                if self.finger_recognizer.is_click_released(angles['idx']):
                    self.click_manager.reset_double_click_hold()
            
            # 드래그 (중지)
            if self.finger_recognizer.is_drag_triggered(angles['mid']):
                if not self.mouse_controller.is_dragging():
                    self.mouse_controller.drag_start()
            else:
                if self.finger_recognizer.is_drag_released(angles['mid']):
                    if self.mouse_controller.is_dragging():
                        self.mouse_controller.drag_end()
            
            hud.append(f"idx@PIP:{angles['idx']:.1f}°  mid@PIP:{angles['mid']:.1f}°")
        
        return frame, hud
    
    def draw_hud(self, frame, hud_lines):
        """
        HUD 그리기
        
        Args:
            frame: 프레임
            hud_lines: HUD 텍스트 리스트
        """
        y = config.HUD_START_Y
        for line in hud_lines:
            color = config.HUD_COLOR_ACTIVE if "ACTIVE" in line or "CURSOR: ON" in line else config.HUD_COLOR_NORMAL
            cv2.putText(frame, line, (10, y), config.HUD_FONT, config.HUD_FONT_SCALE, color, config.HUD_FONT_THICKNESS, cv2.LINE_AA)
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
            print(f"\n원근 보정(Perspective Correction): {'ON' if enabled else 'OFF'}")
        elif key == ord('<'):
            factor = self.state_manager.decrease_factor()
            print(f"\nFactor decreased: {factor:.2f}")
        elif key == ord('>'):
            factor = self.state_manager.increase_factor()
            print(f"\nFactor increased: {factor:.2f}")
        elif key == ord('-'):
            z_margin = self.state_manager.decrease_z_margin()
            print(f"\nZ Margin decreased: {z_margin:.1f}")
        elif key == ord('='):
            z_margin = self.state_manager.increase_z_margin()
            print(f"\nZ Margin increased: {z_margin:.1f}")
        elif key == ord('['):
            hyst = self.state_manager.decrease_hysteresis()
            print(f"\nHysteresis decreased: {hyst:.2f}")
        elif key == ord(']'):
            hyst = self.state_manager.increase_hysteresis()
            print(f"\nHysteresis increased: {hyst:.2f}")
        elif key == ord('r'):
            self.state_manager.reset_baseline()
            print("\nBaseline reset!")
        
        return True
    
    def run(self):
        """메인 루프"""
        if not self.cap.isOpened():
            print("Failed to open webcam.")
            return
        
        print(config.HELP_TEXT)
        
        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break
                
                # 좌우 반전 (거울 모드)
                frame = cv2.flip(frame, 1)
                
                # 프레임 처리
                output, hud = self.process_frame(frame)
                
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