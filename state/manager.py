"""
State Management Module
ACTIVE/IDLE 상태 전환 관리
"""

from filters.ema_filter import EMAFilter
import config


class StateManager:
    """
    ACTIVE/IDLE 상태 관리
    
    Z축 거리 기반 상태 전환 (Hysteresis 적용)
    """
    
    def __init__(self,
                 factor=config.FACTOR,
                 factor_min=config.FACTOR_MIN,
                 factor_max=config.FACTOR_MAX,
                 factor_step=config.FACTOR_STEP,
                 z_margin=config.Z_MARGIN,
                 hysteresis_ratio=config.HYSTERESIS_RATIO,
                 ema_alpha=config.EMA_LEN_ALPHA):
        """
        Args:
            factor: Z 거리 비율 (예: 1.20 = 120%)
            factor_min: Factor 최솟값
            factor_max: Factor 최댓값
            factor_step: Factor 조정 단위
            z_margin: 안전 마진 (픽셀)
            hysteresis_ratio: 떨림 방지 비율
            ema_alpha: EMA 필터 계수
        """
        self.factor = float(factor)
        self.factor_min = float(factor_min)
        self.factor_max = float(factor_max)
        self.factor_step = float(factor_step)
        self.z_margin = float(z_margin)
        self.hysteresis_ratio = float(hysteresis_ratio)
        
        # EMA 필터
        self.ema_filter = EMAFilter(alpha=ema_alpha)
        
        # 상태
        self.active = False
        self.base_len = None
        self._prev_z_len = None
    
    def process_z_distance(self, z_distance):
        """
        Z 거리 처리 및 상태 판정
        
        Args:
            z_distance: 양안 중점 ↔ 검지 끝 Z 거리
        
        Returns:
            dict: {
                'active': 현재 상태,
                'z_len_filtered': 필터링된 Z 거리,
                'base_len': 기준선,
                'threshold_on': ACTIVE 진입 임계값,
                'threshold_off': IDLE 복귀 임계값,
                'state_changed': 상태 변경 여부,
                'new_state': 새로운 상태 (변경된 경우)
            }
        """
        # EMA 필터링
        z_len_filtered = self.ema_filter.update(z_distance)
        
        # 기준선 설정 (처음)
        if self.base_len is None:
            self.base_len = z_len_filtered
        
        # 임계값 계산
        threshold_on = self.base_len * self.factor + self.z_margin
        threshold_off = self.base_len * max(0.8, self.factor * self.hysteresis_ratio) - self.z_margin
        
        # 상태 전환 판정
        state_changed = False
        new_state = self.active
        
        if not self.active and z_len_filtered >= threshold_on:
            # IDLE → ACTIVE
            self.active = True
            state_changed = True
            new_state = True
        elif self.active and z_len_filtered < threshold_off:
            # ACTIVE → IDLE
            self.active = False
            state_changed = True
            new_state = False
        
        self._prev_z_len = z_len_filtered
        
        return {
            'active': self.active,
            'z_len_filtered': z_len_filtered,
            'base_len': self.base_len,
            'threshold_on': threshold_on,
            'threshold_off': threshold_off,
            'state_changed': state_changed,
            'new_state': new_state
        }
    
    def is_active(self):
        """현재 ACTIVE 상태인지 확인"""
        return self.active
    
    def reset_baseline(self):
        """기준선을 현재 필터링된 값으로 리셋"""
        current_value = self.ema_filter.get_value()
        if current_value is not None:
            self.base_len = current_value
    
    def increase_factor(self):
        """Factor 증가 (덜 민감하게)"""
        self.factor = min(self.factor + self.factor_step, self.factor_max)
        return self.factor
    
    def decrease_factor(self):
        """Factor 감소 (더 민감하게)"""
        self.factor = max(self.factor - self.factor_step, self.factor_min)
        return self.factor
    
    def increase_z_margin(self):
        """Z Margin 증가"""
        self.z_margin = min(self.z_margin + 1.0, 50.0)
        return self.z_margin
    
    def decrease_z_margin(self):
        """Z Margin 감소"""
        self.z_margin = max(self.z_margin - 1.0, 0.0)
        return self.z_margin
    
    def increase_hysteresis(self):
        """Hysteresis 증가"""
        self.hysteresis_ratio = min(self.hysteresis_ratio + 0.01, 0.99)
        return self.hysteresis_ratio
    
    def decrease_hysteresis(self):
        """Hysteresis 감소"""
        self.hysteresis_ratio = max(self.hysteresis_ratio - 0.01, 0.80)
        return self.hysteresis_ratio
    
    def get_state_info(self):
        """상태 정보 반환"""
        return {
            'active': self.active,
            'factor': self.factor,
            'z_margin': self.z_margin,
            'hysteresis_ratio': self.hysteresis_ratio,
            'base_len': self.base_len
        }


class ModeManager:
    """
    터치 모드 / 키보드 모드 전환 관리
    """

    TOUCH_MODE = "touch"
    KEYBOARD_MODE = "keyboard"

    def __init__(self):
        self.current_mode = self.TOUCH_MODE

    def toggle_mode(self):
        """모드 토글"""
        if self.current_mode == self.TOUCH_MODE:
            self.current_mode = self.KEYBOARD_MODE
            print("\n[KEYBOARD MODE]")
        else:
            self.current_mode = self.TOUCH_MODE
            print("\n[TOUCH MODE]")

        return self.current_mode

    def is_touch_mode(self):
        """터치 모드인지 확인"""
        return self.current_mode == self.TOUCH_MODE

    def is_keyboard_mode(self):
        """키보드 모드인지 확인"""
        return self.current_mode == self.KEYBOARD_MODE

    def get_mode(self):
        """현재 모드 반환"""
        return self.current_mode