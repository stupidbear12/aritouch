"""
Zoom Control Module
Pinch 제스처 기반 Zoom In/Out 제어
"""

try:
    import win32api
    import win32con
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

import config
from utils.math_utils import clamp
from filters.ema_filter import EMAFilter


class ZoomController:
    """
    Ctrl + Mouse Wheel 기반 Zoom 제어
    """
    
    def __init__(self, wheel_delta=120):
        """
        Args:
            wheel_delta: 마우스 휠 1칸 (기본: 120)
        """
        self.wheel_delta = int(wheel_delta)
        self.windows_available = WINDOWS_AVAILABLE
    
    def zoom_in(self):
        """Zoom In (Ctrl + Wheel Up)"""
        if not self.windows_available:
            return
        
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, +self.wheel_delta, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    
    def zoom_out(self):
        """Zoom Out (Ctrl + Wheel Down)"""
        if not self.windows_available:
            return
        
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -self.wheel_delta, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


class PinchZoomManager:
    """
    Pinch 제스처 기반 Position-based Zoom 관리
    
    - 원근 보정 적용
    - Deadzone, 최대 스텝 제한
    - Zoom 보호 로직
    """
    
    def __init__(self, 
                 px_per_step=30.0,
                 deadzone_px=3.0,
                 max_steps_per_frame=6,
                 z_normalization_enabled=True,
                 min_z_for_normalization=20.0,
                 reference_z_frames=5,
                 ema_alpha=0.5):
        """
        Args:
            px_per_step: Pinch 거리 → Wheel 스텝 변환 비율
            deadzone_px: Deadzone (픽셀)
            max_steps_per_frame: 프레임당 최대 스텝
            z_normalization_enabled: 원근 보정 활성화
            min_z_for_normalization: 최소 Z 거리
            reference_z_frames: 기준 Z 계산용 프레임 수
            ema_alpha: EMA 필터 계수
        """
        self.px_per_step = float(px_per_step)
        self.deadzone_px = float(deadzone_px)
        self.max_steps_per_frame = int(max_steps_per_frame)
        
        # 원근 보정
        self.z_normalization_enabled = z_normalization_enabled
        self.min_z_for_normalization = float(min_z_for_normalization)
        self.reference_z_frames = int(reference_z_frames)
        self.reference_z = None
        self._z_samples = []
        
        # EMA 필터
        self.ema_filter = EMAFilter(alpha=ema_alpha)
        
        # 상태
        self.base_pinch = None
        self.prev_steps_sent = 0
        
        # Zoom 컨트롤러
        self.zoom_controller = ZoomController()
    
    def reset(self):
        """상태 초기화"""
        self.base_pinch = None
        self.prev_steps_sent = 0
        self.reference_z = None
        self._z_samples = []
        self.ema_filter.reset()
    
    def process_pinch(self, pinch_distance, idx_tip_z, thumb_tip_z):
        """
        Pinch 거리 처리 및 Zoom 스텝 계산
        
        Args:
            pinch_distance: 검지-엄지 거리 (픽셀)
            idx_tip_z: 검지 끝 Z 좌표
            thumb_tip_z: 엄지 끝 Z 좌표
        
        Returns:
            (steps_to_fire, info_dict)
            - steps_to_fire: 실행할 Zoom 스텝 수 (양수=In, 음수=Out)
            - info_dict: 디버깅 정보
        """
        info = {
            'raw_pinch': pinch_distance,
            'normalized_pinch': pinch_distance,
            'z_avg': None,
            'reference_z': self.reference_z,
            'z_scale_factor': 1.0,
            'base_pinch': self.base_pinch,
            'delta': 0.0,
            'steps_total': 0,
            'steps_to_fire': 0,
            'collecting_ref_z': False
        }
        
        # 1. 원근 보정 적용
        if self.z_normalization_enabled and idx_tip_z is not None and thumb_tip_z is not None:
            z_avg = (abs(idx_tip_z) + abs(thumb_tip_z)) / 2.0
            info['z_avg'] = z_avg
            
            # Reference Z 설정 (처음 N 프레임 평균)
            if self.reference_z is None:
                if z_avg >= self.min_z_for_normalization:
                    self._z_samples.append(z_avg)
                
                if len(self._z_samples) >= self.reference_z_frames:
                    self.reference_z = float(sum(self._z_samples) / len(self._z_samples))
                    info['reference_z'] = self.reference_z
                else:
                    info['collecting_ref_z'] = True
            
            # 원근 보정 계산
            if self.reference_z is not None and z_avg >= self.min_z_for_normalization:
                z_scale_factor = self.reference_z / z_avg
                normalized_pinch = pinch_distance * z_scale_factor
                info['z_scale_factor'] = z_scale_factor
                info['normalized_pinch'] = normalized_pinch
            else:
                normalized_pinch = pinch_distance
        else:
            normalized_pinch = pinch_distance
        
        # 2. EMA 필터링
        filtered_pinch = self.ema_filter.update(normalized_pinch)
        
        # 3. 기준선 설정
        if self.base_pinch is None:
            # Reference Z가 설정된 후에만 base_pinch 설정
            if not self.z_normalization_enabled or self.reference_z is not None:
                self.base_pinch = filtered_pinch
                self.prev_steps_sent = 0
                info['base_pinch'] = self.base_pinch
        
        # 4. 변화량 계산
        if self.base_pinch is not None:
            delta = filtered_pinch - self.base_pinch
            info['delta'] = delta
            
            if abs(delta) <= self.deadzone_px:
                steps_total = 0
            else:
                steps_total = int(round(delta / self.px_per_step))
            
            info['steps_total'] = steps_total
            
            # 5. 증분만 계산
            steps_to_fire = steps_total - self.prev_steps_sent
            steps_to_fire = int(clamp(steps_to_fire, -self.max_steps_per_frame, self.max_steps_per_frame))
            info['steps_to_fire'] = steps_to_fire
            
            return (steps_to_fire, info)
        else:
            # base_pinch가 설정되지 않음 (reference_z 수집 중)
            return (0, info)
    
    def execute_zoom(self, steps):
        """
        Zoom 실행
        
        Args:
            steps: Zoom 스텝 수 (양수=In, 음수=Out)
        
        Returns:
            실제 실행된 스텝 수
        """
        if steps > 0:
            for _ in range(steps):
                self.zoom_controller.zoom_in()
            self.prev_steps_sent += steps
            return steps
        elif steps < 0:
            for _ in range(-steps):
                self.zoom_controller.zoom_out()
            self.prev_steps_sent += steps
            return steps
        return 0
    
    def toggle_normalization(self):
        """원근 보정 토글"""
        self.z_normalization_enabled = not self.z_normalization_enabled
        # 토글 시 상태 초기화
        self.reset()
        return self.z_normalization_enabled


class ZoomGuard:
    """
    Zoom 보호 로직
    
    - Grace period
    - Edge band
    - Drop guard
    """
    
    def __init__(self,
                 active_grace_ms=180,
                 release_cooldown_ms=280,
                 edge_band=8.0,
                 drop_guard=12.0):
        """
        Args:
            active_grace_ms: ACTIVE 진입 후 대기 시간 (ms)
            release_cooldown_ms: IDLE 복귀 후 대기 시간 (ms)
            edge_band: 경계 부근 보호 (픽셀)
            drop_guard: 급격한 Z 감소 보호 (픽셀)
        """
        self.active_grace_ms = active_grace_ms
        self.release_cooldown_ms = release_cooldown_ms
        self.edge_band = edge_band
        self.drop_guard = drop_guard
        
        self.zoom_block_until = 0
        self._prev_z_len = None
    
    def set_grace_period(self, current_time_ms):
        """Grace period 설정 (ACTIVE 진입 시)"""
        self.zoom_block_until = current_time_ms + self.active_grace_ms
    
    def set_cooldown(self, current_time_ms):
        """Cooldown 설정 (IDLE 복귀 시)"""
        self.zoom_block_until = current_time_ms + self.release_cooldown_ms
    
    def is_zoom_allowed(self, current_time_ms, current_z_len, threshold_on, threshold_off):
        """
        Zoom 허용 여부 확인
        
        Args:
            current_time_ms: 현재 시간 (ms)
            current_z_len: 현재 Z 거리
            threshold_on: ACTIVE 진입 임계값
            threshold_off: IDLE 복귀 임계값
        
        Returns:
            (allowed, reason)
        """
        # 1. 쿨다운 체크
        if current_time_ms < self.zoom_block_until:
            return (False, "cooldown/grace")
        
        # 2. 엣지 밴드 체크 (ACTIVE 경계 부근)
        if current_z_len < (threshold_on + self.edge_band):
            return (False, "edge-band")
        
        # 3. 급격한 Z 감소 체크
        if self._prev_z_len is not None:
            z_drop = self._prev_z_len - current_z_len
            if z_drop > self.drop_guard:
                self.zoom_block_until = current_time_ms + 120
                return (False, "z-drop-guard")
        
        self._prev_z_len = current_z_len
        return (True, "")
    
    def reset(self):
        """상태 초기화"""
        self.zoom_block_until = 0
        self._prev_z_len = None
        