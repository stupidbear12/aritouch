from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from gesture.candidate_scorer import GestureLabel


@dataclass
class ContextInfo:
    screen_type: str = "default"
    focused_widget: str = ""
    allowed_commands: set[GestureLabel] = field(default_factory=lambda: set(GestureLabel))
    prev_label: Optional[GestureLabel] = None


class ContextFusion:

    def __init__(self, use_ml: bool = False):
        self.use_ml = use_ml

    def fuse(
        self,
        label: GestureLabel | None,
        context: ContextInfo,
    ) -> GestureLabel:
        if label is None:
            return GestureLabel.IDLE
        if context.allowed_commands and label not in context.allowed_commands:
            return GestureLabel.IDLE
        return label
