import win32api
import win32con


VK_CONTROL = 0x11


def move_to(x, y):
    win32api.SetCursorPos((int(x), int(y)))


def click_left():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def _ctrl_down():
    win32api.keybd_event(VK_CONTROL, 0, 0, 0)


def _ctrl_up():
    win32api.keybd_event(VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


def ctrl_wheel(ticks: int, wheel_step: int = 120):
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
                step * wheel_step,
                0,
            )
    finally:
        _ctrl_up()
