import ctypes
from ctypes import wintypes

from utils.constants import SPI_SETCURSORS, IDC_ARROW, IDC_HAND

user32 = ctypes.windll.user32


class CursorManager:

    def __init__(self) -> None:
        self._originals: dict[int, int] = {}

    def set_active_cursor(self, shape_id: int = IDC_HAND) -> None:
        source = user32.LoadCursorW(0, shape_id)
        if not source:
            return
        target_id = IDC_ARROW
        if target_id not in self._originals:
            self._originals[target_id] = user32.CopyImage(
                user32.LoadCursorW(0, target_id), 2, 0, 0, 0
            )
        user32.SetSystemCursor(source, target_id)

    def restore(self) -> None:
        user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
        self._originals.clear()
