"""Templates Page displaying curated starter presets for quick QR code creation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.config import GITHUB_PROFILE_URL
from src.core.qr_generator import QRCustomizationConfig, QRGenerator
from src.services.localization import get_i18n
from src.widgets.custom_button import CustomButton
from src.widgets.qr_preview import pil_image_to_qpixmap


@dataclass
class TemplatePreset:
    """Represents a pre-configured QR code starter template."""

    key: str
    qr_type: str
    fields: Dict[str, Any]
    customization: Dict[str, Any]


TEMPLATE_PRESETS: List[TemplatePreset] = [
    TemplatePreset(
        key="website",
        qr_type="url",
        fields={"url": "https://example.com", "strict_validate": True},
        customization={
            "fg_color": "#6C3CE9",
            "bg_color": "#FFFFFF",
            "style": "rounded",
            "error_correction": "M",
            "size": 1024,
        },
    ),
    TemplatePreset(
        key="wifi_guest",
        qr_type="wifi",
        fields={
            "ssid": "QUBIC_Guest_WiFi",
            "password": "WelcomeGuest2026",
            "security": "WPA",
            "hidden": False,
        },
        customization={
            "fg_color": "#101014",
            "bg_color": "#FFFFFF",
            "style": "rounded",
            "error_correction": "Q",
            "size": 1024,
        },
    ),
    TemplatePreset(
        key="business_card",
        qr_type="vcard",
        fields={
            "first_name": "Alex",
            "last_name": "Morgan",
            "phone": "+1 (555) 987-6543",
            "email": "alex.morgan@example.com",
            "organization": "QUBIC Studio",
            "website": "https://example.com",
        },
        customization={
            "fg_color": "#1D1C27",
            "bg_color": "#FFFFFF",
            "style": "classic",
            "error_correction": "M",
            "size": 1024,
        },
    ),
    TemplatePreset(
        key="social_profile",
        qr_type="url",
        fields={"url": GITHUB_PROFILE_URL, "strict_validate": True},
        customization={
            "fg_color": "#9565FF",
            "bg_color": "#FFFFFF",
            "style": "dots",
            "error_correction": "Q",
            "size": 1024,
        },
    ),
    TemplatePreset(
        key="email_support",
        qr_type="email",
        fields={
            "recipient": "support@example.com",
            "subject": "Support Inquiry",
            "message": "Hello, I would like to ask a question about...",
        },
        customization={
            "fg_color": "#059669",
            "bg_color": "#FFFFFF",
            "style": "soft",
            "error_correction": "M",
            "size": 1024,
        },
    ),
    TemplatePreset(
        key="direct_call",
        qr_type="phone",
        fields={"phone": "+1 (555) 234-5678"},
        customization={
            "fg_color": "#2563EB",
            "bg_color": "#FFFFFF",
            "style": "classic",
            "error_correction": "M",
            "size": 1024,
        },
    ),
    TemplatePreset(
        key="sms_feedback",
        qr_type="sms",
        fields={
            "phone": "+1 (555) 234-5678",
            "message": "Hi! I scanned your QR code.",
        },
        customization={
            "fg_color": "#D97706",
            "bg_color": "#FFFFFF",
            "style": "soft",
            "error_correction": "M",
            "size": 1024,
        },
    ),
]


class TemplatesPage(QWidget):
    """Grid of starter templates that can be loaded and customized in the Generator."""

    template_selected = Signal(object, str)  # (TemplatePreset, localized_name)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._i18n = get_i18n()
        self._setup_ui()
        self._i18n.subscribe(self.retranslate_ui)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("PageSubtitle")
        root.addWidget(self.page_title)
        root.addWidget(self.page_subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 8, 0)
        self.grid_layout.setHorizontalSpacing(16)
        self.grid_layout.setVerticalSpacing(16)

        scroll.setWidget(self.grid_container)
        root.addWidget(scroll, 1)

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        t = self._i18n.get
        self.page_title.setText(t("templates.title"))
        self.page_subtitle.setText(t("templates.subtitle"))
        self._rebuild_cards()

    def _rebuild_cards(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for idx, preset in enumerate(TEMPLATE_PRESETS):
            card = self._create_template_card(preset)
            self.grid_layout.addWidget(card, idx // 2, idx % 2)

    def _create_template_card(self, preset: TemplatePreset) -> QFrame:
        t = self._i18n.get
        card = QFrame()
        card.setObjectName("TemplateCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        # Mini QR Preview
        thumb = QLabel()
        thumb.setFixedSize(84, 84)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            cfg = QRCustomizationConfig.from_dict(preset.customization)
            cfg.size = 180
            res = QRGenerator.generate_from_fields(preset.qr_type, preset.fields, cfg)
            pix = pil_image_to_qpixmap(res.image).scaled(
                80,
                80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            thumb.setPixmap(pix)
        except Exception:
            pass
        layout.addWidget(thumb, 0, Qt.AlignmentFlag.AlignTop)

        # Text & button
        col = QVBoxLayout()
        col.setSpacing(6)

        cat_label = QLabel(t(f"templates.items.{preset.key}.category"))
        cat_label.setObjectName("FieldLabel")
        cat_label.setStyleSheet("color: #B28AFF;")
        col.addWidget(cat_label)

        name_text = t(f"templates.items.{preset.key}.name")
        name_label = QLabel(name_text)
        name_label.setObjectName("SectionTitle")
        col.addWidget(name_label)

        desc_label = QLabel(t(f"templates.items.{preset.key}.description"))
        desc_label.setObjectName("HintLabel")
        desc_label.setWordWrap(True)
        col.addWidget(desc_label)

        col.addStretch(1)

        use_btn = CustomButton(t("templates.use_template_btn"), variant="primary")
        use_btn.clicked.connect(
            lambda _c=False, p=preset, nm=name_text: self.template_selected.emit(p, nm)
        )
        col.addWidget(use_btn, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(col, 1)
        return card
