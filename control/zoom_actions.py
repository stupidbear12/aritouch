import win32api
import win32con

VK_CONTROL = 0x11


def _ctrl_down() -> None:
    win32api.keybd_event(VK_CONTROL, 0, 0, 0)


def _ctrl_up() -> None:
    win32api.keybd_event(VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


class ZoomActions:
    def __init__(self, wheel_step: int = 120) -> None:
        self.wheel_step = wheel_step

    def scroll_with_ctrl(self, ticks: int) -> None:
        if ticks == 0:
            return
        _ctrl_down()
        try:
            step = 1 if ticks > 0 else -1
            for _ in range(abs(ticks)):
                win32api.mouse_event(
                    win32con.MOUSEEVENTF_WHEEL,
                    0,
                    0,
                    step * self.wheel_step,
                    0,
                )
        finally:
            _ctrl_up()

    def zoom_in(self, ticks: int = 1) -> None:
        self.scroll_with_ctrl(abs(ticks))

    def zoom_out(self, ticks: int = 1) -> None:
        self.scroll_with_ctrl(-abs(ticks))

