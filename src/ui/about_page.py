"""Polished About Page displaying application branding, developer attribution, and tech stack."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.config import DEVELOPER_NAME, GITHUB_PROFILE_URL, get_resource_path
from src.services.localization import get_i18n
from src.widgets.custom_button import CustomButton


class AboutPage(QWidget):
    """Displays QUBIC branding, version 1.0.0, developer Kemorovv, and clickable GitHub profile."""

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
        root.addWidget(self.page_title)

        # Brand Hero Card
        hero_card = QFrame()
        hero_card.setObjectName("Card")
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(22)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(92, 92)
        icon_path = get_resource_path("assets/icon.png")
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(
                92,
                92,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.icon_label.setPixmap(pix)
        hero_layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignTop)

        hero_text_col = QVBoxLayout()
        hero_text_col.setSpacing(6)

        title_row = QHBoxLayout()
        self.app_name_label = QLabel("QUBIC")
        self.app_name_label.setObjectName("PageTitle")
        self.version_label = QLabel()
        self.version_label.setObjectName("VersionBadge")
        title_row.addWidget(self.app_name_label)
        title_row.addWidget(self.version_label)
        title_row.addStretch(1)
        hero_text_col.addLayout(title_row)

        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("SectionTitle")
        self.subtitle_label.setStyleSheet("color: #B28AFF;")
        hero_text_col.addWidget(self.subtitle_label)

        self.desc_label = QLabel()
        self.desc_label.setObjectName("PageSubtitle")
        self.desc_label.setWordWrap(True)
        hero_text_col.addWidget(self.desc_label)

        hero_layout.addLayout(hero_text_col, 1)
        root.addWidget(hero_card)

        # Developer Attribution Card
        dev_card = QFrame()
        dev_card.setObjectName("Card")
        dev_layout = QVBoxLayout(dev_card)
        dev_layout.setContentsMargins(22, 18, 22, 18)
        dev_layout.setSpacing(10)

        self.dev_section_title = QLabel()
        self.dev_section_title.setObjectName("SectionTitle")
        dev_layout.addWidget(self.dev_section_title)

        dev_row = QHBoxLayout()
        self.dev_label = QLabel()
        self.dev_label.setObjectName("FieldLabel")
        self.dev_value = QLabel(DEVELOPER_NAME)
        dev_row.addWidget(self.dev_label)
        dev_row.addWidget(self.dev_value)
        dev_row.addStretch(1)
        dev_layout.addLayout(dev_row)

        gh_row = QHBoxLayout()
        self.gh_label = QLabel()
        self.gh_label.setObjectName("FieldLabel")
        self.gh_link_label = QLabel(
            f'<a href="{GITHUB_PROFILE_URL}" style="color: #9565FF; text-decoration: none;">{GITHUB_PROFILE_URL}</a>'
        )
        self.gh_link_label.setOpenExternalLinks(True)
        self.gh_link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

        self.gh_open_btn = CustomButton("", variant="primary")
        self.gh_open_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(GITHUB_PROFILE_URL))
        )

        gh_row.addWidget(self.gh_label)
        gh_row.addWidget(self.gh_link_label)
        gh_row.addStretch(1)
        gh_row.addWidget(self.gh_open_btn)
        dev_layout.addLayout(gh_row)

        root.addWidget(dev_card)

        # Technology Stack Card
        tech_card = QFrame()
        tech_card.setObjectName("Card")
        tech_layout = QVBoxLayout(tech_card)
        tech_layout.setContentsMargins(22, 18, 22, 18)
        tech_layout.setSpacing(8)

        self.tech_section_title = QLabel()
        self.tech_section_title.setObjectName("SectionTitle")
        tech_layout.addWidget(self.tech_section_title)

        self.tech_labels = [QLabel() for _ in range(5)]
        for lbl in self.tech_labels:
            lbl.setObjectName("PageSubtitle")
            tech_layout.addWidget(lbl)

        self.license_label = QLabel()
        self.license_label.setObjectName("HintLabel")
        tech_layout.addWidget(self.license_label)

        root.addWidget(tech_card)
        root.addStretch(1)

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        t = self._i18n.get
        self.page_title.setText(t("about.title"))
        self.version_label.setText(t("about.version"))
        self.subtitle_label.setText(t("about.subtitle"))
        self.desc_label.setText(t("about.description"))

        self.dev_section_title.setText(t("about.developer_section"))
        self.dev_label.setText(f"{t('about.developer_label')}:")
        self.gh_label.setText(f"{t('about.github_label')}:")
        self.gh_open_btn.setText(t("about.github_btn"))

        self.tech_section_title.setText(t("about.tech_section"))
        keys = (
            "about.tech_python",
            "about.tech_pyside",
            "about.tech_qrcode",
            "about.tech_sqlite",
            "about.tech_pyinstaller",
        )
        for lbl, key in zip(self.tech_labels, keys):
            lbl.setText(f"• {t(key)}")

        self.license_label.setText(t("about.license_label"))
