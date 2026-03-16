import win32api
import win32con


class MouseController:
    def move_to(self, x: int, y: int) -> None:
        win32api.SetCursorPos((int(x), int(y)))

    def click_left(self) -> None:
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def right_click(self) -> None:
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

