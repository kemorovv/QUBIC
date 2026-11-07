"""Non-intrusive floating toast notification banner for QUBIC."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class NotificationBanner(QFrame):
    """Floating notification bar displayed at the bottom-right of the main window."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("NotificationBanner")
        self.setVisible(False)
        self.setFixedHeight(48)
        self.setMinimumWidth(320)
        self.setMaximumWidth(560)

        self._action_callback: Optional[Callable[[], None]] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 12, 8)
        layout.setSpacing(12)

        self.status_dot = QLabel("●")
        layout.addWidget(self.status_dot)

        self.message_label = QLabel()
        self.message_label.setWordWrap(False)
        layout.addWidget(self.message_label, 1)

        self.action_btn = QPushButton()
        self.action_btn.setObjectName("SecondaryButton")
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setVisible(False)
        self.action_btn.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.action_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #9994AA; font-weight: bold; }"
            "QPushButton:hover { color: #F5F2FF; }"
        )
        self.close_btn.clicked.connect(self.hide_toast)
        layout.addWidget(self.close_btn)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_toast)

    def show_message(
        self,
        message: str,
        level: str = "success",
        duration_ms: int = 4000,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Display the notification banner with optional action button."""
        self.setProperty("level", level)
        dot_color = "#65D6A0" if level == "success" else ("#FF6B78" if level == "error" else "#9565FF")
        self.status_dot.setStyleSheet(f"color: {dot_color}; font-size: 14px;")
        self.message_label.setText(message)

        self._action_callback = action_callback
        if action_text and action_callback is not None:
            self.action_btn.setText(action_text)
            self.action_btn.setVisible(True)
        else:
            self.action_btn.setVisible(False)

        self.style().unpolish(self)
        self.style().polish(self)
        self.adjustSize()
        self.reposition()
        self.setVisible(True)
        self.raise_()
        self._timer.start(duration_ms)

    def hide_toast(self) -> None:
        self._timer.stop()
        self.setVisible(False)

    def reposition(self) -> None:
        """Position banner neatly at the bottom-right of its parent widget."""
        parent = self.parentWidget()
        if parent is None:
            return
        margin_x = 24
        margin_y = 24
        w = min(max(self.sizeHint().width(), 340), parent.width() - 2 * margin_x)
        self.setFixedWidth(w)
        x = parent.width() - w - margin_x
        y = parent.height() - self.height() - margin_y
        self.move(max(margin_x, x), max(margin_y, y))

    def _on_action_clicked(self) -> None:
        cb = self._action_callback
        self.hide_toast()
        if cb is not None:
            cb()
