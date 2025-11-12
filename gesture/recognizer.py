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