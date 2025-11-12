"""
Mouse Control Module
마우스 클릭, 드래그 제어
"""

try:
    import win32api
    import win32con
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    print("Warning: win32api not available. Mouse control disabled.")


class MouseController:
    """
    마우스 제어 클래스
    
    클릭, 더블클릭, 드래그 기능 제공
    """
    
    def __init__(self):
        self.dragging = False
        self.windows_available = WINDOWS_AVAILABLE
    
    def click(self):
        """마우스 왼쪽 버튼 클릭"""
        if not self.windows_available:
            return
        
        x, y = win32api.GetCursorPos()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    
    def double_click(self):
        """마우스 왼쪽 버튼 더블클릭"""
        if not self.windows_available:
            return
        
        x, y = win32api.GetCursorPos()
        for _ in range(2):
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    
    def drag_start(self):
        """드래그 시작 (왼쪽 버튼 누른 상태 유지)"""
        if not self.windows_available:
            return
        
        if not self.dragging:
            x, y = win32api.GetCursorPos()
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            self.dragging = True
    
    def drag_end(self):
        """드래그 종료 (왼쪽 버튼 떼기)"""
        if not self.windows_available:
            return
        
        if self.dragging:
            x, y = win32api.GetCursorPos()
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            self.dragging = False
    
    def is_dragging(self):
        """현재 드래그 중인지 확인"""
        return self.dragging
    
    def force_release(self):
        """강제로 마우스 버튼 해제 (종료 시 사용)"""
        if self.dragging:
            self.drag_end()
    
    def get_cursor_position(self):
        """현재 커서 위치 반환"""
        if not self.windows_available:
            return (0, 0)
        return win32api.GetCursorPos()
    
    def set_cursor_position(self, x, y):
        """커서 위치 설정"""
        if not self.windows_available:
            return
        win32api.SetCursorPos((int(x), int(y)))


class ClickManager:
    """
    클릭 이벤트 관리
    
    Refractory period, 더블클릭 홀드 등 관리
    """
    
    def __init__(self, refractory_ms=250, double_click_hold_ms=2000):
        """
        Args:
            refractory_ms: 클릭 후 불응기 (ms)
            double_click_hold_ms: 더블클릭 홀드 시간 (ms)
        """
        self.refractory_ms = refractory_ms
        self.double_click_hold_ms = double_click_hold_ms
        
        self.last_click_time = 0
        self.double_click_hold_start = None
        self.double_click_fired = False
    
    def can_click(self, current_time_ms):
        """
        클릭 가능 여부 확인 (refractory period)
        
        Args:
            current_time_ms: 현재 시간 (밀리초)
        
        Returns:
            클릭 가능 여부 (bool)
        """
        return (current_time_ms - self.last_click_time) > self.refractory_ms
    
    def register_click(self, current_time_ms):
        """
        클릭 발생 기록
        
        Args:
            current_time_ms: 현재 시간 (밀리초)
        """
        self.last_click_time = current_time_ms
    
    def start_double_click_hold(self, current_time_ms):
        """더블클릭 홀드 시작"""
        if self.double_click_hold_start is None:
            self.double_click_hold_start = current_time_ms
            self.double_click_fired = False
    
    def check_double_click_hold(self, current_time_ms):
        """
        더블클릭 홀드 시간 확인
        
        Args:
            current_time_ms: 현재 시간 (밀리초)
        
        Returns:
            더블클릭 발동 여부 (bool)
        """
        if self.double_click_hold_start is None:
            return False
        
        if self.double_click_fired:
            return False
        
        hold_time = current_time_ms - self.double_click_hold_start
        if hold_time >= self.double_click_hold_ms:
            self.double_click_fired = True
            return True
        
        return False
    
    def reset_double_click_hold(self):
        """더블클릭 홀드 초기화"""
        self.double_click_hold_start = None
        self.double_click_fired = False