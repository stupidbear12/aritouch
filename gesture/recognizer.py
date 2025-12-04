"""
Gesture Recognition Module
손가락 각도 기반 제스처 인식 (클릭, 드래그)
Pinch 거리 계산
"""

from utils.math_utils import angle_at_joint, l2_distance
import config


class FingerGestureRecognizer:
    """
    손가락 구부림 각도 기반 제스처 인식
    
    - 클릭: 검지 구부림
    - 드래그: 중지 구부림
    """
    
    def __init__(self,
                 click_in_angle=config.THETA_CLICK_IN,
                 click_out_angle=config.THETA_CLICK_OUT,
                 drag_in_angle=config.THETA_DRAG_IN,
                 drag_out_angle=config.THETA_DRAG_OUT):
        """
        Args:
            click_in_angle: 클릭 트리거 각도
            click_out_angle: 클릭 해제 각도
            drag_in_angle: 드래그 트리거 각도
            drag_out_angle: 드래그 해제 각도
        """
        self.click_in_angle = click_in_angle
        self.click_out_angle = click_out_angle
        self.drag_in_angle = drag_in_angle
        self.drag_out_angle = drag_out_angle
    
    def calculate_finger_angles(self, landmarks_2d):
        """
        손가락 관절 각도 계산
        
        Args:
            landmarks_2d: 2D 랜드마크 dict (from HandDetector.get_landmarks_2d)
        
        Returns:
            dict: {'idx': index_angle, 'mid': middle_angle}
        """
        # 검지 각도 (PIP 관절 기준)
        idx_angle = angle_at_joint(
            landmarks_2d['idx_mcp'],
            landmarks_2d['idx_pip'],
            landmarks_2d['idx_dip']
        )
        
        # 중지 각도 (PIP 관절 기준)
        mid_angle = angle_at_joint(
            landmarks_2d['mid_mcp'],
            landmarks_2d['mid_pip'],
            landmarks_2d['mid_dip']
        )
        
        return {
            'idx': idx_angle,
            'mid': mid_angle
        }
    
    def is_click_triggered(self, index_angle):
        """
        클릭 트리거 확인
        
        Args:
            index_angle: 검지 각도
        
        Returns:
            bool: 클릭 트리거 여부
        """
        return index_angle <= self.click_in_angle
    
    def is_click_released(self, index_angle):
        """
        클릭 해제 확인 (Hysteresis)
        
        Args:
            index_angle: 검지 각도
        
        Returns:
            bool: 클릭 해제 여부
        """
        return index_angle >= self.click_out_angle
    
    def is_drag_triggered(self, middle_angle):
        """
        드래그 트리거 확인
        
        Args:
            middle_angle: 중지 각도
        
        Returns:
            bool: 드래그 트리거 여부
        """
        return middle_angle <= self.drag_in_angle
    
    def is_drag_released(self, middle_angle):
        """
        드래그 해제 확인 (Hysteresis)
        
        Args:
            middle_angle: 중지 각도
        
        Returns:
            bool: 드래그 해제 여부
        """
        return middle_angle >= self.drag_out_angle


class PinchRecognizer:
    """
    Pinch 제스처 인식
    
    검지 끝 ↔ 엄지 끝 거리 계산
    """
    
    def calculate_pinch_distance(self, landmarks_2d):
        """
        Pinch 거리 계산 (2D)
        
        Args:
            landmarks_2d: 2D 랜드마크 dict
        
        Returns:
            float: Pinch 거리 (픽셀)
        """
        return l2_distance(landmarks_2d['idx_tip'], landmarks_2d['thm_tip'])


class ShakaModeRecognizer:
    """
    엄지+새끼 제스처 (Shaka 제스처) 인식

    모드 전환용 제스처:
    - 엄지: 펴짐
    - 검지, 중지, 약지: 접힘
    - 새끼: 펴짐
    - 2초 이상 유지 시 모드 전환
    """

    def __init__(self, hold_duration_ms=2000):
        """
        Args:
            hold_duration_ms: 제스처 유지 시간 (밀리초)
        """
        self.hold_duration_ms = hold_duration_ms
        self.gesture_start_time = None
        self.gesture_confirmed = False

    def is_shaka_gesture(self, landmarks_2d):
        """
        엄지+새끼만 펴진 상태 확인

        Args:
            landmarks_2d: 2D 랜드마크 dict

        Returns:
            bool: Shaka 제스처 여부
        """
        from utils.math_utils import angle_at_joint

        # 엄지 펴짐 판단 (CMC-MCP-IP 각도)
        thumb_angle = angle_at_joint(
            landmarks_2d['thm_cmc'],
            landmarks_2d['thm_mcp'],
            landmarks_2d['thm_ip']
        )

        # 검지 각도
        index_angle = angle_at_joint(
            landmarks_2d['idx_mcp'],
            landmarks_2d['idx_pip'],
            landmarks_2d['idx_dip']
        )

        # 중지 각도
        middle_angle = angle_at_joint(
            landmarks_2d['mid_mcp'],
            landmarks_2d['mid_pip'],
            landmarks_2d['mid_dip']
        )

        # 약지 각도
        ring_angle = angle_at_joint(
            landmarks_2d['ring_mcp'],
            landmarks_2d['ring_pip'],
            landmarks_2d['ring_dip']
        )

        # 새끼 각도
        pinky_angle = angle_at_joint(
            landmarks_2d['pinky_mcp'],
            landmarks_2d['pinky_pip'],
            landmarks_2d['pinky_dip']
        )

        # 판정 기준
        thumb_extended = thumb_angle > 150      # 엄지 펴짐
        index_curled = index_angle < 140        # 검지 접힘
        middle_curled = middle_angle < 140      # 중지 접힘
        ring_curled = ring_angle < 140          # 약지 접힘
        pinky_extended = pinky_angle > 150      # 새끼 펴짐

        is_shaka = (thumb_extended and
                    index_curled and
                    middle_curled and
                    ring_curled and
                    pinky_extended)

        return is_shaka

    def check_hold_duration(self, is_shaka, current_time_ms):
        """
        2초 홀드 확인

        Args:
            is_shaka: Shaka 제스처 여부
            current_time_ms: 현재 시간 (밀리초)

        Returns:
            (bool, float): (모드 전환 트리거, 진행률 0.0~1.0)
        """
        if is_shaka:
            if self.gesture_start_time is None:
                # 제스처 시작
                self.gesture_start_time = current_time_ms
                self.gesture_confirmed = False

            elapsed = current_time_ms - self.gesture_start_time
            progress = min(1.0, elapsed / self.hold_duration_ms)

            if elapsed >= self.hold_duration_ms and not self.gesture_confirmed:
                # 2초 완료 - 모드 전환 트리거
                self.gesture_confirmed = True
                return (True, 1.0)

            return (False, progress)
        else:
            # 제스처 해제
            self.gesture_start_time = None
            self.gesture_confirmed = False
            return (False, 0.0)

    def reset(self):
        """상태 초기화"""
        self.gesture_start_time = None
        self.gesture_confirmed = False