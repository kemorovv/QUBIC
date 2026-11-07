"""Live QR Code Preview and Export Panel widget for the right side of the Generator workspace."""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config import EXPORT_FORMATS, MAX_CUSTOM_QR_SIZE, MIN_CUSTOM_QR_SIZE
from src.core.qr_generator import GeneratedQRResult
from src.services.localization import get_i18n
from src.widgets.custom_button import CustomButton


def pil_image_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Convert a PIL RGBA/RGB Image to a QPixmap without temporary disk files."""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    qimg = QImage.fromData(buf.getvalue(), "PNG")
    return QPixmap.fromImage(qimg)


class QRPreviewWidget(QFrame):
    """Right-hand panel displaying either a clean empty state or the generated QR code + export controls."""

    export_requested = Signal(str, int, bool)  # (format, size_px, transparent_bg)
    copy_requested = Signal()
    open_folder_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PreviewCard")
        self._i18n = get_i18n()
        self._current_result: Optional[GeneratedQRResult] = None
        self._last_saved_folder: Optional[str] = None

        self._setup_ui()
        self._i18n.subscribe(self.retranslate_ui)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        self.header_label = QLabel()
        self.header_label.setObjectName("SectionTitle")
        root.addWidget(self.header_label)

        # Preview surface container
        self.surface = QFrame()
        self.surface.setObjectName("PreviewSurface")
        self.surface.setMinimumSize(280, 280)
        self.surface.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        surface_layout = QVBoxLayout(self.surface)
        surface_layout.setContentsMargins(18, 18, 18, 18)
        surface_layout.setSpacing(10)
        surface_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Empty State Widget
        self.empty_container = QWidget()
        empty_layout = QVBoxLayout(self.empty_container)
        empty_layout.setContentsMargins(12, 12, 12, 12)
        empty_layout.setSpacing(8)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_icon_label = QLabel()
        self.empty_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_icon_label.setPixmap(self._draw_empty_state_icon())
        empty_layout.addWidget(self.empty_icon_label)

        self.empty_title_label = QLabel()
        self.empty_title_label.setObjectName("SectionTitle")
        self.empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title_label)

        self.empty_subtitle_label = QLabel()
        self.empty_subtitle_label.setObjectName("HintLabel")
        self.empty_subtitle_label.setWordWrap(True)
        self.empty_subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_subtitle_label)

        surface_layout.addWidget(self.empty_container)

        # QR Image Label
        self.qr_image_label = QLabel()
        self.qr_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_image_label.setVisible(False)
        surface_layout.addWidget(self.qr_image_label, 1)

        root.addWidget(self.surface, 1)

        # Metadata labels
        meta_row = QHBoxLayout()
        self.meta_size_label = QLabel()
        self.meta_size_label.setObjectName("HintLabel")
        self.meta_ecc_label = QLabel()
        self.meta_ecc_label.setObjectName("HintLabel")
        self.meta_ecc_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        meta_row.addWidget(self.meta_size_label)
        meta_row.addStretch(1)
        meta_row.addWidget(self.meta_ecc_label)
        root.addLayout(meta_row)

        # Export section
        self.export_title_label = QLabel()
        self.export_title_label.setObjectName("SectionTitle")
        root.addWidget(self.export_title_label)

        fmt_size_row = QHBoxLayout()
        fmt_size_row.setSpacing(10)

        fmt_col = QVBoxLayout()
        fmt_col.setSpacing(4)
        self.format_label = QLabel()
        self.format_label.setObjectName("FieldLabel")
        self.format_combo = QComboBox()
        for fmt in EXPORT_FORMATS:
            self.format_combo.addItem(fmt, fmt)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        fmt_col.addWidget(self.format_label)
        fmt_col.addWidget(self.format_combo)
        fmt_size_row.addLayout(fmt_col, 1)

        size_col = QVBoxLayout()
        size_col.setSpacing(4)
        self.export_size_label = QLabel()
        self.export_size_label.setObjectName("FieldLabel")
        self.export_size_spin = QSpinBox()
        self.export_size_spin.setRange(MIN_CUSTOM_QR_SIZE, MAX_CUSTOM_QR_SIZE)
        self.export_size_spin.setSingleStep(64)
        self.export_size_spin.setValue(1024)
        size_col.addWidget(self.export_size_label)
        size_col.addWidget(self.export_size_spin)
        fmt_size_row.addLayout(size_col, 1)

        root.addLayout(fmt_size_row)

        self.transparent_checkbox = QCheckBox()
        root.addWidget(self.transparent_checkbox)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.export_btn = CustomButton("", variant="primary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._emit_export)
        btn_row.addWidget(self.export_btn, 2)

        self.copy_btn = CustomButton("", variant="secondary")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self.copy_btn, 1)

        root.addLayout(btn_row)

        self.open_folder_btn = CustomButton("", variant="secondary")
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.clicked.connect(self.open_folder_requested.emit)
        root.addWidget(self.open_folder_btn)

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        self.header_label.setText(self._i18n.get("preview.title"))
        self.empty_title_label.setText(self._i18n.get("preview.empty_title"))
        self.empty_subtitle_label.setText(self._i18n.get("preview.empty_subtitle"))
        self.export_title_label.setText(self._i18n.get("preview.export_section_title"))
        self.format_label.setText(self._i18n.get("preview.format_label"))
        self.export_size_label.setText(self._i18n.get("preview.export_size_label"))
        self.transparent_checkbox.setText(self._i18n.get("preview.transparent_bg_checkbox"))
        self.export_btn.setText(self._i18n.get("preview.export_btn"))
        self.copy_btn.setText(self._i18n.get("preview.quick_copy_btn"))
        self.open_folder_btn.setText(self._i18n.get("preview.open_folder_btn"))
        self._update_meta_labels()

    @property
    def current_result(self) -> Optional[GeneratedQRResult]:
        return self._current_result

    def set_qr_result(self, result: GeneratedQRResult) -> None:
        """Display the generated QR code in the preview pane."""
        self._current_result = result
        self.empty_container.setVisible(False)
        self.qr_image_label.setVisible(True)
        self.export_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.export_size_spin.setValue(result.config.size)
        self.transparent_checkbox.setChecked(result.config.transparent_bg)
        self._render_scaled_pixmap()
        self._update_meta_labels()

    def clear_preview(self) -> None:
        """Reset preview back to its initial empty state."""
        self._current_result = None
        self.qr_image_label.clear()
        self.qr_image_label.setVisible(False)
        self.empty_container.setVisible(True)
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.meta_size_label.setText("")
        self.meta_ecc_label.setText("")

    def set_export_defaults(self, fmt: str, size: int) -> None:
        idx = self.format_combo.findData(fmt.upper())
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)
        self.export_size_spin.setValue(size)

    def show_open_folder_button(self, folder_path: str) -> None:
        self._last_saved_folder = folder_path
        self.open_folder_btn.setVisible(True)

    @property
    def last_saved_folder(self) -> Optional[str]:
        return self._last_saved_folder

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._current_result is not None:
            self._render_scaled_pixmap()

    def _render_scaled_pixmap(self) -> None:
        if self._current_result is None:
            return
        pix = pil_image_to_qpixmap(self._current_result.image)
        avail_w = max(180, self.surface.width() - 40)
        avail_h = max(180, self.surface.height() - 40)
        side = min(avail_w, avail_h, 340)
        scaled = pix.scaled(
            side,
            side,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.qr_image_label.setPixmap(scaled)

    def _update_meta_labels(self) -> None:
        if self._current_result is None:
            self.meta_size_label.setText("")
            self.meta_ecc_label.setText("")
            return
        cfg = self._current_result.config
        style_label = self._i18n.get(f"customization.style_{cfg.style}")
        self.meta_size_label.setText(self._i18n.get("preview.meta_size", size=cfg.size))
        self.meta_ecc_label.setText(
            self._i18n.get("preview.meta_ecc", ecc=cfg.error_correction, style=style_label)
        )

    def _on_format_changed(self) -> None:
        fmt = self.format_combo.currentData()
        is_jpg = fmt == "JPG"
        self.transparent_checkbox.setEnabled(not is_jpg)
        if is_jpg:
            self.transparent_checkbox.setChecked(False)

    def _emit_export(self) -> None:
        fmt = str(self.format_combo.currentData() or "PNG")
        size = int(self.export_size_spin.value())
        transparent = bool(self.transparent_checkbox.isChecked()) and fmt != "JPG"
        self.export_requested.emit(fmt, size, transparent)

    def _copy_to_clipboard(self) -> None:
        if self._current_result is None:
            return
        pix = pil_image_to_qpixmap(self._current_result.image)
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setPixmap(pix)
        self.copy_requested.emit()

    @staticmethod
    def _draw_empty_state_icon() -> QPixmap:
        pix = QPixmap(72, 72)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#9565FF"), 2.5)
        painter.setPen(pen)
        painter.drawRoundedRect(10, 10, 20, 20, 4, 4)
        painter.drawRoundedRect(42, 10, 20, 20, 4, 4)
        painter.drawRoundedRect(10, 42, 20, 20, 4, 4)
        painter.setBrush(QColor("#B28AFF"))
        painter.drawRoundedRect(42, 42, 8, 8, 2, 2)
        painter.drawRoundedRect(54, 54, 8, 8, 2, 2)
        painter.drawRoundedRect(42, 54, 8, 8, 2, 2)
        painter.end()
        return pix
