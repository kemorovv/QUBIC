"""Compact, modern left navigation sidebar with vector icons and localized labels."""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.config import get_resource_path
from src.services.localization import get_i18n
from src.widgets.custom_button import CustomButton


class Sidebar(QFrame):
    """Left navigation sidebar displaying branding and 5 main section buttons."""

    navigation_Selected = Signal(str)

    NAV_ITEMS = ("generator", "history", "templates", "settings", "about")

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(232)
        self._i18n = get_i18n()
        self._buttons: Dict[str, CustomButton] = {}
        self._active_key: str = "generator"

        self._setup_ui()
        self._i18n.subscribe(self.retranslate_ui)
        self.retranslate_ui()
        self.set_active_page("generator")

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 22, 16, 18)
        root.setSpacing(8)

        # Brand Header
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(4, 0, 4, 16)
        brand_row.setSpacing(12)

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(42, 42)
        icon_path = get_resource_path("assets/icon.png")
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(
                42,
                42,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_label.setPixmap(pix)
        brand_row.addWidget(self.logo_label)

        brand_text_col = QVBoxLayout()
        brand_text_col.setContentsMargins(0, 0, 0, 0)
        brand_text_col.setSpacing(2)
        self.brand_title = QLabel("QUBIC")
        self.brand_title.setObjectName("BrandTitle")
        self.brand_subtitle = QLabel("QR Code Studio")
        self.brand_subtitle.setObjectName("BrandSubtitle")
        brand_text_col.addWidget(self.brand_title)
        brand_text_col.addWidget(self.brand_subtitle)
        brand_row.addLayout(brand_text_col, 1)

        root.addLayout(brand_row)

        # Navigation Buttons
        for key in self.NAV_ITEMS:
            btn = CustomButton("", variant="nav")
            btn.setIcon(self._build_nav_icon(key, "#9565FF"))
            btn.setIconSize(QSize(18, 18))
            btn.clicked.connect(lambda _checked=False, k=key: self._on_nav_clicked(k))
            root.addWidget(btn)
            self._buttons[key] = btn

        root.addStretch(1)

        # Version Badge Footer
        footer_row = QHBoxLayout()
        self.version_badge = QLabel("v1.0.0")
        self.version_badge.setObjectName("VersionBadge")
        footer_row.addWidget(self.version_badge)
        footer_row.addStretch(1)
        root.addLayout(footer_row)

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        self.brand_title.setText(self._i18n.get("app.name"))
        self.brand_subtitle.setText(self._i18n.get("app.subtitle"))
        self.version_badge.setText(self._i18n.get("nav.version_label"))
        for key, btn in self._buttons.items():
            btn.setText(f"  {self._i18n.get(f'nav.{key}')}")

    def set_active_page(self, page_key: str) -> None:
        if page_key not in self._buttons:
            return
        self._active_key = page_key
        for key, btn in self._buttons.items():
            is_active = key == page_key
            btn.set_active(is_active)
            icon_color = "#B28AFF" if is_active else "#9994AA"
            btn.setIcon(self._build_nav_icon(key, icon_color))

    def _on_nav_clicked(self, page_key: str) -> None:
        self.set_active_page(page_key)
        self.navigation_Selected.emit(page_key)

    @staticmethod
    def _build_nav_icon(key: str, color_hex: str) -> QIcon:
        pix = QPixmap(20, 20)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color_hex), 1.8)
        painter.setPen(pen)

        if key == "generator":
            painter.drawRoundedRect(2, 2, 6, 6, 1.5, 1.5)
            painter.drawRoundedRect(12, 2, 6, 6, 1.5, 1.5)
            painter.drawRoundedRect(2, 12, 6, 6, 1.5, 1.5)
            painter.drawRect(12, 12, 3, 3)
            painter.drawRect(15, 15, 3, 3)
        elif key == "history":
            painter.drawEllipse(2, 2, 16, 16)
            painter.drawLine(10, 6, 10, 10)
            painter.drawLine(10, 10, 14, 12)
        elif key == "templates":
            painter.drawRoundedRect(2, 2, 16, 6, 2, 2)
            painter.drawRoundedRect(2, 11, 7, 7, 2, 2)
            painter.drawRoundedRect(11, 11, 7, 7, 2, 2)
        elif key == "settings":
            painter.drawEllipse(6, 6, 8, 8)
            painter.drawLine(10, 2, 10, 4)
            painter.drawLine(10, 16, 10, 18)
            painter.drawLine(2, 10, 4, 10)
            painter.drawLine(16, 10, 18, 10)
        elif key == "about":
            painter.drawEllipse(2, 2, 16, 16)
            painter.drawLine(10, 9, 10, 14)
            painter.drawPoint(10, 6)

        painter.end()
        return QIcon(pix)
