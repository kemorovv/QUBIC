"""Interactive HEX Color Picker widget with validation, swatch dialog, and recent colors."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.image_processor import normalize_hex_color, validate_hex_color
from src.services.localization import get_i18n
from src.widgets.custom_button import CustomButton


class ColorPickerWidget(QWidget):
    """Provides a color swatch button, validated HEX input, and color dialog trigger."""

    color_changed = Signal(str)

    def __init__(
        self,
        label_key: str,
        initial_color: str = "#000000",
        default_color: str = "#000000",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = get_i18n()
        self._label_key = label_key
        self._default_color = normalize_hex_color(default_color)
        self._current_color = normalize_hex_color(initial_color)

        self._setup_ui()
        self._i18n.subscribe(self.retranslate_ui)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.label = QLabel()
        self.label.setObjectName("FieldLabel")
        root.addWidget(self.label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.swatch_btn = QPushButton()
        self.swatch_btn.setFixedSize(34, 34)
        self.swatch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.swatch_btn.clicked.connect(self._open_color_dialog)
        row.addWidget(self.swatch_btn)

        self.hex_input = QLineEdit(self._current_color)
        self.hex_input.setMaxLength(7)
        self.hex_input.textEdited.connect(self._on_hex_edited)
        self.hex_input.editingFinished.connect(self._on_editing_finished)
        row.addWidget(self.hex_input, 1)

        self.pick_btn = CustomButton("", variant="secondary")
        self.pick_btn.clicked.connect(self._open_color_dialog)
        row.addWidget(self.pick_btn)

        root.addLayout(row)

        self.error_label = QLabel()
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        self._update_swatch_style()

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        """Update localized labels and tooltips."""
        self.label.setText(self._i18n.get(self._label_key))
        self.pick_btn.setText(self._i18n.get("customization.pick_color_btn"))
        self.hex_input.setPlaceholderText(self._i18n.get("customization.hex_placeholder"))
        self.error_label.setText(self._i18n.get("customization.invalid_hex"))

    @property
    def color(self) -> str:
        """Return the current validated HEX color."""
        return self._current_color

    def set_color(self, hex_color: str, emit_signal: bool = True) -> None:
        """Programmatically set the current color."""
        if not validate_hex_color(hex_color):
            return
        normalized = normalize_hex_color(hex_color)
        self._current_color = normalized
        self.hex_input.blockSignals(True)
        self.hex_input.setText(normalized)
        self.hex_input.blockSignals(False)
        self._set_invalid_state(False)
        self._update_swatch_style()
        if emit_signal:
            self.color_changed.emit(normalized)

    def reset_to_default(self, emit_signal: bool = True) -> None:
        """Reset color to its default value."""
        self.set_color(self._default_color, emit_signal=emit_signal)

    def _on_hex_edited(self, text: str) -> None:
        if validate_hex_color(text):
            self._current_color = normalize_hex_color(text)
            self._set_invalid_state(False)
            self._update_swatch_style()
            self.color_changed.emit(self._current_color)
        else:
            self._set_invalid_state(True)

    def _on_editing_finished(self) -> None:
        text = self.hex_input.text().strip()
        if validate_hex_color(text):
            normalized = normalize_hex_color(text)
            self.hex_input.setText(normalized)
            self._set_invalid_state(False)
        else:
            # Restore last valid color if user leaves invalid text
            self.hex_input.setText(self._current_color)
            self._set_invalid_state(False)

    def _open_color_dialog(self) -> None:
        initial = QColor(self._current_color)
        chosen = QColorDialog.getColor(initial, self, self.label.text())
        if chosen.isValid():
            self.set_color(chosen.name().upper(), emit_signal=True)

    def _set_invalid_state(self, invalid: bool) -> None:
        self.hex_input.setProperty("invalid", "true" if invalid else "false")
        self.error_label.setVisible(invalid)
        self.hex_input.style().unpolish(self.hex_input)
        self.hex_input.style().polish(self.hex_input)

    def _update_swatch_style(self) -> None:
        self.swatch_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {self._current_color};"
            f"  border: 2px solid #302B3D;"
            f"  border-radius: 8px;"
            f"}}"
            f"QPushButton:hover {{ border: 2px solid #9565FF; }}"
        )


class RecentColorsBar(QWidget):
    """Displays a row of clickable recent/preset color swatches."""

    swatch_clicked = Signal(str)

    def __init__(
        self,
        colors: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = get_i18n()
        self._colors: List[str] = list(colors or [])
        self._buttons: List[QPushButton] = []

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(6)

        self.title_label = QLabel()
        self.title_label.setObjectName("HintLabel")
        self._root.addWidget(self.title_label)

        self._swatch_row = QHBoxLayout()
        self._swatch_row.setContentsMargins(0, 0, 0, 0)
        self._swatch_row.setSpacing(6)
        self._root.addLayout(self._swatch_row)

        self._rebuild_swatches()
        self._i18n.subscribe(self.retranslate_ui)
        self.retranslate_ui()

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        self.title_label.setText(self._i18n.get("customization.recent_colors_label"))

    def set_colors(self, colors: List[str]) -> None:
        self._colors = list(colors[:10])
        self._rebuild_swatches()

    def _rebuild_swatches(self) -> None:
        while self._swatch_row.count():
            item = self._swatch_row.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._buttons.clear()

        for hex_code in self._colors[:10]:
            if not validate_hex_color(hex_code):
                continue
            norm = normalize_hex_color(hex_code)
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(norm)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {norm}; border: 1px solid #302B3D; border-radius: 6px; }}"
                f"QPushButton:hover {{ border: 2px solid #9565FF; }}"
            )
            btn.clicked.connect(lambda _checked=False, c=norm: self.swatch_clicked.emit(c))
            self._swatch_row.addWidget(btn)
            self._buttons.append(btn)
        self._swatch_row.addStretch(1)
