"""Styled custom buttons with cursor and active-state helpers for QUBIC."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget


class CustomButton(QPushButton):
    """Reusable QPushButton with semantic variant styling ('primary', 'secondary', 'danger', 'chip')."""

    VARIANT_OBJECT_NAMES = {
        "primary": "PrimaryButton",
        "secondary": "SecondaryButton",
        "danger": "DangerButton",
        "type_chip": "TypeChip",
        "style_chip": "StyleChip",
        "nav": "NavButton",
    }

    def __init__(
        self,
        text: str = "",
        variant: str = "secondary",
        checkable: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(checkable)
        obj_name = self.VARIANT_OBJECT_NAMES.get(variant, "SecondaryButton")
        self.setObjectName(obj_name)

    def set_active(self, active: bool) -> None:
        """Update dynamic 'active' property and refresh widget stylesheet state."""
        self.setProperty("active", "true" if active else "false")
        if self.isCheckable():
            self.setChecked(active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
