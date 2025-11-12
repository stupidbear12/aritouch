"""
Cursor Control Module
커서 위치 매핑 및 모양 변경
"""

import ctypes
try:
    import win32api
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

from utils.math_utils import clamp
from filters.ema_filter import MultiEMAFilter
import config


class CursorMapper:
    """
    손 좌표 → 화면 커서 좌표 매핑
    
    EMA 필터링, 미러 모드, 이동 임계값 처리 포함
    """
    
    def __init__(self, screen_width=None, screen_height=None, 
                 ema_alpha=0.6, move_threshold=1, mirror=False):
        """
        Args:
            screen_width: 화면 너비 (None이면 자동 감지)
            screen_height: 화면 높이 (None이면 자동 감지)
            ema_alpha: EMA 필터 계수
            move_threshold: 커서 이동 최소 거리 (픽셀)
            mirror: 좌우 반전 모드
        """
        # 화면 크기
        if screen_width is None or screen_height is None:
            if WINDOWS_AVAILABLE:
                self.screen_width = win32api.GetSystemMetrics(0)
                self.screen_height = win32api.GetSystemMetrics(1)
            else:
                self.screen_width = 1920
                self.screen_height = 1080
        else:
            self.screen_width = screen_width
            self.screen_height = screen_height
        
        # EMA 필터 (X, Y 좌표)
        self.ema_filter = MultiEMAFilter(alpha=ema_alpha, dimensions=2)
        
        # 설정
        self.move_threshold = move_threshold
        self.mirror = mirror
        
        # 마지막 전송한 좌표
        self._last_sent = None
    
    def map_to_screen(self, normalized_x, normalized_y):
        """
        정규화된 좌표 (0~1)를 화면 좌표로 변환
        
        Args:
            normalized_x: 정규화된 X 좌표 (0~1)
            normalized_y: 정규화된 Y 좌표 (0~1)
        
        Returns:
            (screen_x, screen_y) - 화면 좌표 (픽셀)
        """
        # 미러 모드 적용
        if self.mirror:
            normalized_x = 1.0 - normalized_x
        
        # 화면 좌표로 변환
        screen_x = clamp(normalized_x, 0.0, 1.0) * self.screen_width
        screen_y = clamp(normalized_y, 0.0, 1.0) * self.screen_height
        
        # EMA 필터 적용
        filtered_x, filtered_y = self.ema_filter.update((screen_x, screen_y))
        
        # 정수로 변환 및 범위 제한
        final_x = int(clamp(filtered_x, 0, self.screen_width - 1))
        final_y = int(clamp(filtered_y, 0, self.screen_height - 1))
        
        # 이동 임계값 체크
        should_move = False
        if self._last_sent is None:
            should_move = True
        else:
            dx = abs(final_x - self._last_sent[0])
            dy = abs(final_y - self._last_sent[1])
            if dx >= self.move_threshold or dy >= self.move_threshold:
                should_move = True
        
        if should_move:
            self._last_sent = (final_x, final_y)
            return (final_x, final_y, True)  # 이동됨
        else:
            return (final_x, final_y, False)  # 이동 안 됨
    
    def toggle_mirror(self):
        """미러 모드 토글"""
        self.mirror = not self.mirror
        return self.mirror
    
    def set_mirror(self, enabled):
        """미러 모드 설정"""
        self.mirror = enabled
    
    def reset(self):
        """필터 초기화"""
        self.ema_filter.reset()
        self._last_sent = None


class SystemCursorChanger:
    """
    Windows 시스템 커서 모양 변경
    
    ACTIVE 상태에서 커서를 손 모양으로 변경
    """
    
    def __init__(self, enabled=True, active_cursor_shape=config.IDC_HAND):
        """
        Args:
            enabled: 커서 변경 활성화 여부
            active_cursor_shape: ACTIVE 시 커서 모양 (IDC_* 상수)
        """
        self.enabled = enabled
        self.active_cursor_shape = active_cursor_shape
        self._cursor_changed = False
        self.windows_available = WINDOWS_AVAILABLE
    
    def apply_active_cursor(self):
        """ACTIVE 커서 적용 (손 모양 등)"""
        if not self.windows_available or not self.enabled or self._cursor_changed:
            return False
        
        try:
            hcur = ctypes.windll.user32.LoadCursorW(None, ctypes.c_void_p(self.active_cursor_shape))
            ctypes.windll.user32.SetSystemCursor(hcur, config.IDC_ARROW)
            self._cursor_changed = True
            return True
        except Exception as e:
            print(f"Failed to change cursor: {e}")
            return False
    
    def restore_cursor(self):
        """원래 커서로 복원"""
        if not self.windows_available or not self._cursor_changed:
            return False
        
        try:
            ctypes.windll.user32.SystemParametersInfoW(config.SPI_SETCURSORS, 0, None, 0)
            self._cursor_changed = False
            return True
        except Exception as e:
            print(f"Failed to restore cursor: {e}")
            return False
    
    def is_changed(self):
        """커서가 변경된 상태인지 확인"""
        return self._cursor_changed
    
    def set_enabled(self, enabled):
        """커서 변경 기능 활성화/비활성화"""
        self.enabled = enabled