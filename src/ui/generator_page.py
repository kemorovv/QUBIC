"""Main QR Code Generator workspace page with all 7 payload types, customization, and export."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    DEFAULT_BG_COLOR,
    DEFAULT_FG_COLOR,
    MAX_CUSTOM_QR_SIZE,
    MIN_CUSTOM_QR_SIZE,
    QR_OUTPUT_SIZES,
    QR_STYLES,
    QR_TYPES,
)
from src.core.image_processor import compute_contrast_ratio
from src.core.qr_exporter import QRExporter, get_default_export_filename
from src.core.qr_generator import GeneratedQRResult, QRCustomizationConfig, QRGenerator
from src.core.qr_payloads import PayloadValidationError
from src.database.history_repository import HistoryRepository
from src.services.localization import get_i18n
from src.services.settings_service import SettingsService
from src.widgets.color_picker import ColorPickerWidget, RecentColorsBar
from src.widgets.custom_button import CustomButton
from src.widgets.qr_preview import QRPreviewWidget


def open_directory_in_os(folder_path: str) -> None:
    """Open the given folder in the user's native operating system file explorer."""
    path = Path(folder_path).resolve()
    if not path.exists():
        return
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


class GeneratorPage(QWidget):
    """Comprehensive QR code creation, customization, preview, and export workspace."""

    notification_requested = Signal(str, str, str, object)  # (message, level, action_text, callback)
    history_updated = Signal()

    MAX_TEXT_LENGTH = 2000

    def __init__(
        self,
        settings_service: SettingsService,
        history_repo: HistoryRepository,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = get_i18n()
        self._settings = settings_service
        self._history_repo = history_repo

        self._active_type: str = "url"
        self._active_style: str = "classic"
        self._logo_path: Optional[str] = None
        self._type_buttons: Dict[str, CustomButton] = {}
        self._style_buttons: Dict[str, CustomButton] = {}

        self._setup_ui()
        self._load_initial_preferences()
        self._i18n.subscribe(self.retranslate_ui)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(16)

        # Page Title Header
        header_col = QVBoxLayout()
        header_col.setSpacing(4)
        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("PageSubtitle")
        header_col.addWidget(self.page_title)
        header_col.addWidget(self.page_subtitle)
        outer.addLayout(header_col)

        # Main 2-column workspace
        workspace_row = QHBoxLayout()
        workspace_row.setSpacing(20)

        # Left scrollable column (Inputs + Customization)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(16)

        left_layout.addWidget(self._build_type_selector_card())
        left_layout.addWidget(self._build_content_inputs_card())
        left_layout.addWidget(self._build_customization_card())
        left_layout.addStretch(1)

        scroll.setWidget(left_container)
        workspace_row.addWidget(scroll, 7)

        # Right column (Live Preview + Export)
        self.preview_widget = QRPreviewWidget()
        self.preview_widget.setMinimumWidth(340)
        self.preview_widget.setMaximumWidth(430)
        self.preview_widget.export_requested.connect(self._on_export_requested)
        self.preview_widget.copy_requested.connect(self._on_copy_requested)
        self.preview_widget.open_folder_requested.connect(self._on_open_last_folder)
        workspace_row.addWidget(self.preview_widget, 5)

        outer.addLayout(workspace_row, 1)

    def _build_type_selector_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        self.type_section_label = QLabel()
        self.type_section_label.setObjectName("SectionTitle")
        layout.addWidget(self.type_section_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        for idx, qtype in enumerate(QR_TYPES):
            btn = CustomButton("", variant="type_chip", checkable=True)
            btn.clicked.connect(lambda _checked=False, qt=qtype: self.set_qr_type(qt))
            grid.addWidget(btn, idx // 4, idx % 4)
            self._type_buttons[qtype] = btn

        layout.addLayout(grid)
        return card

    def _build_content_inputs_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        self.content_section_label = QLabel()
        self.content_section_label.setObjectName("SectionTitle")
        layout.addWidget(self.content_section_label)

        self.forms_stack = QStackedWidget()
        self.forms_stack.addWidget(self._create_url_form())
        self.forms_stack.addWidget(self._create_text_form())
        self.forms_stack.addWidget(self._create_wifi_form())
        self.forms_stack.addWidget(self._create_email_form())
        self.forms_stack.addWidget(self._create_phone_form())
        self.forms_stack.addWidget(self._create_sms_form())
        self.forms_stack.addWidget(self._create_vcard_form())
        layout.addWidget(self.forms_stack)

        self.validation_error_label = QLabel()
        self.validation_error_label.setObjectName("ErrorLabel")
        self.validation_error_label.setWordWrap(True)
        self.validation_error_label.setVisible(False)
        layout.addWidget(self.validation_error_label)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.generate_btn = CustomButton("", variant="primary")
        self.generate_btn.clicked.connect(self.generate_qr)
        action_row.addWidget(self.generate_btn, 3)

        self.reset_form_btn = CustomButton("", variant="secondary")
        self.reset_form_btn.clicked.connect(self.clear_current_form)
        action_row.addWidget(self.reset_form_btn, 1)

        layout.addLayout(action_row)
        return card

    def _create_url_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        self.url_label = QLabel()
        self.url_label.setObjectName("FieldLabel")
        self.url_input = QLineEdit()
        self.url_validate_cb = QCheckBox()
        self.url_validate_cb.setChecked(True)
        self.url_hint_label = QLabel()
        self.url_hint_label.setObjectName("HintLabel")
        v.addWidget(self.url_label)
        v.addWidget(self.url_input)
        v.addWidget(self.url_validate_cb)
        v.addWidget(self.url_hint_label)
        v.addStretch(1)
        return w

    def _create_text_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.text_label = QLabel()
        self.text_label.setObjectName("FieldLabel")
        self.text_input = QPlainTextEdit()
        self.text_input.setFixedHeight(110)
        self.text_input.textChanged.connect(self._update_text_char_counter)
        self.text_char_label = QLabel()
        self.text_char_label.setObjectName("HintLabel")
        self.text_char_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        v.addWidget(self.text_label)
        v.addWidget(self.text_input)
        v.addWidget(self.text_char_label)
        v.addStretch(1)
        return w

    def _create_wifi_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        self.wifi_ssid_label = QLabel()
        self.wifi_ssid_label.setObjectName("FieldLabel")
        self.wifi_ssid_input = QLineEdit()
        v.addWidget(self.wifi_ssid_label)
        v.addWidget(self.wifi_ssid_input)

        self.wifi_pass_label = QLabel()
        self.wifi_pass_label.setObjectName("FieldLabel")
        pass_row = QHBoxLayout()
        pass_row.setSpacing(8)
        self.wifi_pass_input = QLineEdit()
        self.wifi_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.wifi_toggle_pass_btn = CustomButton("", variant="secondary")
        self.wifi_toggle_pass_btn.clicked.connect(self._toggle_wifi_password)
        pass_row.addWidget(self.wifi_pass_input, 1)
        pass_row.addWidget(self.wifi_toggle_pass_btn)
        v.addWidget(self.wifi_pass_label)
        v.addLayout(pass_row)

        sec_row = QHBoxLayout()
        sec_row.setSpacing(12)
        sec_col = QVBoxLayout()
        self.wifi_sec_label = QLabel()
        self.wifi_sec_label.setObjectName("FieldLabel")
        self.wifi_sec_combo = QComboBox()
        self.wifi_sec_combo.addItem("WPA / WPA2 / WPA3", "WPA")
        self.wifi_sec_combo.addItem("WEP", "WEP")
        self.wifi_sec_combo.addItem("Open", "nopass")
        self.wifi_sec_combo.currentIndexChanged.connect(self._on_wifi_security_changed)
        sec_col.addWidget(self.wifi_sec_label)
        sec_col.addWidget(self.wifi_sec_combo)
        sec_row.addLayout(sec_col, 1)

        self.wifi_hidden_cb = QCheckBox()
        sec_row.addWidget(self.wifi_hidden_cb, 0, Qt.AlignmentFlag.AlignBottom)
        v.addLayout(sec_row)
        v.addStretch(1)
        return w

    def _create_email_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        self.email_to_label = QLabel()
        self.email_to_label.setObjectName("FieldLabel")
        self.email_to_input = QLineEdit()
        self.email_subj_label = QLabel()
        self.email_subj_label.setObjectName("FieldLabel")
        self.email_subj_input = QLineEdit()
        self.email_msg_label = QLabel()
        self.email_msg_label.setObjectName("FieldLabel")
        self.email_msg_input = QPlainTextEdit()
        self.email_msg_input.setFixedHeight(80)
        v.addWidget(self.email_to_label)
        v.addWidget(self.email_to_input)
        v.addWidget(self.email_subj_label)
        v.addWidget(self.email_subj_input)
        v.addWidget(self.email_msg_label)
        v.addWidget(self.email_msg_input)
        v.addStretch(1)
        return w

    def _create_phone_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        self.phone_label = QLabel()
        self.phone_label.setObjectName("FieldLabel")
        self.phone_input = QLineEdit()
        v.addWidget(self.phone_label)
        v.addWidget(self.phone_input)
        v.addStretch(1)
        return w

    def _create_sms_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        self.sms_phone_label = QLabel()
        self.sms_phone_label.setObjectName("FieldLabel")
        self.sms_phone_input = QLineEdit()
        self.sms_msg_label = QLabel()
        self.sms_msg_label.setObjectName("FieldLabel")
        self.sms_msg_input = QPlainTextEdit()
        self.sms_msg_input.setFixedHeight(80)
        v.addWidget(self.sms_phone_label)
        v.addWidget(self.sms_phone_input)
        v.addWidget(self.sms_msg_label)
        v.addWidget(self.sms_msg_input)
        v.addStretch(1)
        return w

    def _create_vcard_form(self) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.vcard_fn_label = QLabel()
        self.vcard_fn_label.setObjectName("FieldLabel")
        self.vcard_fn_input = QLineEdit()
        self.vcard_ln_label = QLabel()
        self.vcard_ln_label.setObjectName("FieldLabel")
        self.vcard_ln_input = QLineEdit()

        self.vcard_phone_label = QLabel()
        self.vcard_phone_label.setObjectName("FieldLabel")
        self.vcard_phone_input = QLineEdit()
        self.vcard_email_label = QLabel()
        self.vcard_email_label.setObjectName("FieldLabel")
        self.vcard_email_input = QLineEdit()

        self.vcard_org_label = QLabel()
        self.vcard_org_label.setObjectName("FieldLabel")
        self.vcard_org_input = QLineEdit()
        self.vcard_web_label = QLabel()
        self.vcard_web_label.setObjectName("FieldLabel")
        self.vcard_web_input = QLineEdit()

        grid.addWidget(self.vcard_fn_label, 0, 0)
        grid.addWidget(self.vcard_ln_label, 0, 1)
        grid.addWidget(self.vcard_fn_input, 1, 0)
        grid.addWidget(self.vcard_ln_input, 1, 1)

        grid.addWidget(self.vcard_phone_label, 2, 0)
        grid.addWidget(self.vcard_email_label, 2, 1)
        grid.addWidget(self.vcard_phone_input, 3, 0)
        grid.addWidget(self.vcard_email_input, 3, 1)

        grid.addWidget(self.vcard_org_label, 4, 0)
        grid.addWidget(self.vcard_web_label, 4, 1)
        grid.addWidget(self.vcard_org_input, 5, 0)
        grid.addWidget(self.vcard_web_input, 5, 1)
        return w

    def _build_customization_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        self.cust_section_label = QLabel()
        self.cust_section_label.setObjectName("SectionTitle")
        layout.addWidget(self.cust_section_label)

        # Colors Row
        colors_header = QHBoxLayout()
        self.colors_title_label = QLabel()
        self.colors_title_label.setObjectName("FieldLabel")
        self.reset_colors_btn = CustomButton("", variant="secondary")
        self.reset_colors_btn.clicked.connect(self._reset_colors)
        colors_header.addWidget(self.colors_title_label)
        colors_header.addStretch(1)
        colors_header.addWidget(self.reset_colors_btn)
        layout.addLayout(colors_header)

        pickers_row = QHBoxLayout()
        pickers_row.setSpacing(12)
        self.fg_picker = ColorPickerWidget(
            "customization.fg_color_label",
            initial_color=DEFAULT_FG_COLOR,
            default_color=DEFAULT_FG_COLOR,
        )
        self.fg_picker.color_changed.connect(self._on_color_changed)
        self.bg_picker = ColorPickerWidget(
            "customization.bg_color_label",
            initial_color=DEFAULT_BG_COLOR,
            default_color=DEFAULT_BG_COLOR,
        )
        self.bg_picker.color_changed.connect(self._on_color_changed)
        pickers_row.addWidget(self.fg_picker, 1)
        pickers_row.addWidget(self.bg_picker, 1)
        layout.addLayout(pickers_row)

        self.recent_colors_bar = RecentColorsBar(self._settings.get("recent_colors", []))
        self.recent_colors_bar.swatch_clicked.connect(self._on_recent_swatch_clicked)
        layout.addWidget(self.recent_colors_bar)

        self.contrast_warning_label = QLabel()
        self.contrast_warning_label.setObjectName("WarningLabel")
        self.contrast_warning_label.setWordWrap(True)
        self.contrast_warning_label.setVisible(False)
        layout.addWidget(self.contrast_warning_label)

        # QR Module Style Presets
        self.style_title_label = QLabel()
        self.style_title_label.setObjectName("FieldLabel")
        layout.addWidget(self.style_title_label)

        style_row = QHBoxLayout()
        style_row.setSpacing(8)
        for st in QR_STYLES:
            btn = CustomButton("", variant="style_chip", checkable=True)
            btn.clicked.connect(lambda _checked=False, s=st: self.set_qr_style(s))
            style_row.addWidget(btn, 1)
            self._style_buttons[st] = btn
        layout.addLayout(style_row)

        # Error Correction & Output Size Row
        ecc_size_row = QHBoxLayout()
        ecc_size_row.setSpacing(12)

        ecc_col = QVBoxLayout()
        ecc_col.setSpacing(4)
        self.ecc_title_label = QLabel()
        self.ecc_title_label.setObjectName("FieldLabel")
        self.ecc_combo = QComboBox()
        for code in ("L", "M", "Q", "H"):
            self.ecc_combo.addItem(code, code)
        self.ecc_combo.setCurrentIndex(1)  # Default M
        ecc_col.addWidget(self.ecc_title_label)
        ecc_col.addWidget(self.ecc_combo)
        ecc_size_row.addLayout(ecc_col, 1)

        size_col = QVBoxLayout()
        size_col.setSpacing(4)
        self.size_title_label = QLabel()
        self.size_title_label.setObjectName("FieldLabel")
        self.size_combo = QComboBox()
        for sz in QR_OUTPUT_SIZES:
            self.size_combo.addItem(f"{sz} × {sz}", sz)
        self.size_combo.addItem("Custom", "custom")
        self.size_combo.setCurrentIndex(2)  # Default 1024
        self.size_combo.currentIndexChanged.connect(self._on_size_combo_changed)
        size_col.addWidget(self.size_title_label)
        size_col.addWidget(self.size_combo)
        ecc_size_row.addLayout(size_col, 1)

        layout.addLayout(ecc_size_row)

        # Custom Size Spinbox Row
        self.custom_size_container = QWidget()
        cs_row = QHBoxLayout(self.custom_size_container)
        cs_row.setContentsMargins(0, 0, 0, 0)
        self.custom_size_label = QLabel()
        self.custom_size_label.setObjectName("FieldLabel")
        self.custom_size_spin = QSpinBox()
        self.custom_size_spin.setRange(MIN_CUSTOM_QR_SIZE, MAX_CUSTOM_QR_SIZE)
        self.custom_size_spin.setSingleStep(64)
        self.custom_size_spin.setValue(1024)
        cs_row.addWidget(self.custom_size_label)
        cs_row.addWidget(self.custom_size_spin)
        self.custom_size_container.setVisible(False)
        layout.addWidget(self.custom_size_container)

        # Center Logo Integration
        self.logo_title_label = QLabel()
        self.logo_title_label.setObjectName("FieldLabel")
        layout.addWidget(self.logo_title_label)

        logo_btn_row = QHBoxLayout()
        logo_btn_row.setSpacing(8)
        self.logo_upload_btn = CustomButton("", variant="secondary")
        self.logo_upload_btn.clicked.connect(self._choose_logo_file)
        self.logo_remove_btn = CustomButton("", variant="danger")
        self.logo_remove_btn.setVisible(False)
        self.logo_remove_btn.clicked.connect(self._remove_logo)
        self.logo_file_label = QLabel()
        self.logo_file_label.setObjectName("HintLabel")
        logo_btn_row.addWidget(self.logo_upload_btn)
        logo_btn_row.addWidget(self.logo_remove_btn)
        logo_btn_row.addWidget(self.logo_file_label, 1)
        layout.addLayout(logo_btn_row)

        self.logo_scale_label = QLabel()
        self.logo_scale_label.setObjectName("FieldLabel")
        self.logo_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_scale_slider.setRange(10, 25)
        self.logo_scale_slider.setValue(20)
        self.logo_scale_slider.valueChanged.connect(self._update_logo_scale_label)
        layout.addWidget(self.logo_scale_label)
        layout.addWidget(self.logo_scale_slider)

        self.logo_white_bg_cb = QCheckBox()
        self.logo_white_bg_cb.setChecked(True)
        layout.addWidget(self.logo_white_bg_cb)

        self.logo_warning_label = QLabel()
        self.logo_warning_label.setObjectName("WarningLabel")
        self.logo_warning_label.setWordWrap(True)
        self.logo_warning_label.setVisible(False)
        layout.addWidget(self.logo_warning_label)

        return card

    def _load_initial_preferences(self) -> None:
        self.set_qr_type("url")
        default_ecc = str(self._settings.get("default_error_correction", "M"))
        default_size = int(self._settings.get("default_qr_size", 1024))
        default_fmt = str(self._settings.get("default_export_format", "PNG"))

        if self._settings.get("remember_last_settings", True):
            last_cust = self._settings.get("last_customization", {})
            if isinstance(last_cust, dict):
                self.fg_picker.set_color(str(last_cust.get("fg_color", DEFAULT_FG_COLOR)), emit_signal=False)
                self.bg_picker.set_color(str(last_cust.get("bg_color", DEFAULT_BG_COLOR)), emit_signal=False)
                self.set_qr_style(str(last_cust.get("style", "classic")))
                default_ecc = str(last_cust.get("error_correction", default_ecc))
                default_size = int(last_cust.get("size", default_size))
        else:
            self.set_qr_style("classic")

        ecc_idx = self.ecc_combo.findData(default_ecc)
        if ecc_idx >= 0:
            self.ecc_combo.setCurrentIndex(ecc_idx)

        size_idx = self.size_combo.findData(default_size)
        if size_idx >= 0:
            self.size_combo.setCurrentIndex(size_idx)
        else:
            self.size_combo.setCurrentIndex(self.size_combo.findData("custom"))
            self.custom_size_spin.setValue(default_size)

        self.preview_widget.set_export_defaults(default_fmt, default_size)
        self._check_color_contrast()

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        """Translate all labels, buttons, placeholders, and tooltips on the Generator page."""
        t = self._i18n.get
        self.page_title.setText(t("generator.title"))
        self.page_subtitle.setText(t("generator.subtitle"))
        self.type_section_label.setText(t("generator.type_section"))
        self.content_section_label.setText(t("generator.content_section"))
        self.cust_section_label.setText(t("generator.customization_section"))
        self.generate_btn.setText(t("generator.generate_btn"))
        self.reset_form_btn.setText(t("generator.reset_form_btn"))

        for qtype, btn in self._type_buttons.items():
            btn.setText(t(f"qr_types.{qtype}"))

        # URL Form
        self.url_label.setText(t("generator.url_label"))
        self.url_input.setPlaceholderText(t("generator.url_placeholder"))
        self.url_validate_cb.setText(t("generator.url_validate_checkbox"))
        self.url_hint_label.setText(t("generator.url_auto_scheme_hint"))

        # Text Form
        self.text_label.setText(t("generator.text_label"))
        self.text_input.setPlaceholderText(t("generator.text_placeholder"))
        self._update_text_char_counter()

        # Wi-Fi Form
        self.wifi_ssid_label.setText(t("generator.wifi_ssid_label"))
        self.wifi_ssid_input.setPlaceholderText(t("generator.wifi_ssid_placeholder"))
        self.wifi_pass_label.setText(t("generator.wifi_password_label"))
        self.wifi_pass_input.setPlaceholderText(t("generator.wifi_password_placeholder"))
        self._update_wifi_toggle_text()
        self.wifi_sec_label.setText(t("generator.wifi_security_label"))
        self.wifi_sec_combo.setItemText(0, t("generator.wifi_security_wpa"))
        self.wifi_sec_combo.setItemText(1, t("generator.wifi_security_wep"))
        self.wifi_sec_combo.setItemText(2, t("generator.wifi_security_nopass"))
        self.wifi_hidden_cb.setText(t("generator.wifi_hidden_checkbox"))

        # Email Form
        self.email_to_label.setText(t("generator.email_recipient_label"))
        self.email_to_input.setPlaceholderText(t("generator.email_recipient_placeholder"))
        self.email_subj_label.setText(t("generator.email_subject_label"))
        self.email_subj_input.setPlaceholderText(t("generator.email_subject_placeholder"))
        self.email_msg_label.setText(t("generator.email_message_label"))
        self.email_msg_input.setPlaceholderText(t("generator.email_message_placeholder"))

        # Phone Form
        self.phone_label.setText(t("generator.phone_label"))
        self.phone_input.setPlaceholderText(t("generator.phone_placeholder"))

        # SMS Form
        self.sms_phone_label.setText(t("generator.sms_phone_label"))
        self.sms_phone_input.setPlaceholderText(t("generator.sms_phone_placeholder"))
        self.sms_msg_label.setText(t("generator.sms_message_label"))
        self.sms_msg_input.setPlaceholderText(t("generator.sms_message_placeholder"))

        # vCard Form
        self.vcard_fn_label.setText(t("generator.vcard_first_name_label"))
        self.vcard_fn_input.setPlaceholderText(t("generator.vcard_first_name_placeholder"))
        self.vcard_ln_label.setText(t("generator.vcard_last_name_label"))
        self.vcard_ln_input.setPlaceholderText(t("generator.vcard_last_name_placeholder"))
        self.vcard_phone_label.setText(t("generator.vcard_phone_label"))
        self.vcard_phone_input.setPlaceholderText(t("generator.vcard_phone_placeholder"))
        self.vcard_email_label.setText(t("generator.vcard_email_label"))
        self.vcard_email_input.setPlaceholderText(t("generator.vcard_email_placeholder"))
        self.vcard_org_label.setText(t("generator.vcard_org_label"))
        self.vcard_org_input.setPlaceholderText(t("generator.vcard_org_placeholder"))
        self.vcard_web_label.setText(t("generator.vcard_website_label"))
        self.vcard_web_input.setPlaceholderText(t("generator.vcard_website_placeholder"))

        # Customization
        self.colors_title_label.setText(t("customization.colors_title"))
        self.reset_colors_btn.setText(t("customization.reset_colors_btn"))
        self.contrast_warning_label.setText(t("customization.low_contrast_warning"))
        self.style_title_label.setText(t("customization.style_title"))
        for st, btn in self._style_buttons.items():
            btn.setText(t(f"customization.style_{st}"))

        self.ecc_title_label.setText(t("customization.ecc_title"))
        self.ecc_title_label.setToolTip(t("customization.ecc_tooltip"))
        self.ecc_combo.setToolTip(t("customization.ecc_tooltip"))
        self.ecc_combo.setItemText(0, t("customization.ecc_l"))
        self.ecc_combo.setItemText(1, t("customization.ecc_m"))
        self.ecc_combo.setItemText(2, t("customization.ecc_q"))
        self.ecc_combo.setItemText(3, t("customization.ecc_h"))

        self.size_title_label.setText(t("customization.size_title"))
        self.size_combo.setItemText(0, t("customization.size_256"))
        self.size_combo.setItemText(1, t("customization.size_512"))
        self.size_combo.setItemText(2, t("customization.size_1024"))
        self.size_combo.setItemText(3, t("customization.size_2048"))
        self.size_combo.setItemText(4, t("customization.size_custom"))
        self.custom_size_label.setText(t("customization.custom_size_label"))

        self.logo_title_label.setText(t("customization.logo_title"))
        self.logo_upload_btn.setText(t("customization.logo_upload_btn"))
        self.logo_remove_btn.setText(t("customization.logo_remove_btn"))
        if not self._logo_path:
            self.logo_file_label.setText(t("customization.logo_no_file"))
        self._update_logo_scale_label()
        self.logo_white_bg_cb.setText(t("customization.logo_white_bg_checkbox"))
        self.logo_warning_label.setText(t("customization.logo_warning"))

    def set_qr_type(self, qr_type: str) -> None:
        if qr_type not in QR_TYPES:
            return
        self._active_type = qr_type
        for qt, btn in self._type_buttons.items():
            btn.set_active(qt == qr_type)
        self.forms_stack.setCurrentIndex(QR_TYPES.index(qr_type))
        self.validation_error_label.setVisible(False)

    def set_qr_style(self, style_name: str) -> None:
        norm = style_name if style_name in QR_STYLES else "classic"
        self._active_style = norm
        for st, btn in self._style_buttons.items():
            btn.set_active(st == norm)

    def collect_current_fields(self) -> Dict[str, Any]:
        """Collect input values from the currently active QR type form."""
        qt = self._active_type
        if qt == "url":
            return {
                "url": self.url_input.text(),
                "strict_validate": self.url_validate_cb.isChecked(),
            }
        if qt == "text":
            return {"text": self.text_input.toPlainText()[: self.MAX_TEXT_LENGTH]}
        if qt == "wifi":
            return {
                "ssid": self.wifi_ssid_input.text(),
                "password": self.wifi_pass_input.text(),
                "security": str(self.wifi_sec_combo.currentData() or "WPA"),
                "hidden": self.wifi_hidden_cb.isChecked(),
            }
        if qt == "email":
            return {
                "recipient": self.email_to_input.text(),
                "subject": self.email_subj_input.text(),
                "message": self.email_msg_input.toPlainText(),
            }
        if qt == "phone":
            return {"phone": self.phone_input.text()}
        if qt == "sms":
            return {
                "phone": self.sms_phone_input.text(),
                "message": self.sms_msg_input.toPlainText(),
            }
        if qt == "vcard":
            return {
                "first_name": self.vcard_fn_input.text(),
                "last_name": self.vcard_ln_input.text(),
                "phone": self.vcard_phone_input.text(),
                "email": self.vcard_email_input.text(),
                "organization": self.vcard_org_input.text(),
                "website": self.vcard_web_input.text(),
            }
        return {}

    def collect_customization_config(self) -> QRCustomizationConfig:
        """Build QRCustomizationConfig from the UI customization controls."""
        size_data = self.size_combo.currentData()
        selected_size = int(self.custom_size_spin.value()) if size_data == "custom" else int(size_data or 1024)
        return QRCustomizationConfig(
            fg_color=self.fg_picker.color,
            bg_color=self.bg_picker.color,
            style=self._active_style,
            error_correction=str(self.ecc_combo.currentData() or "M"),
            size=selected_size,
            transparent_bg=self.preview_widget.transparent_checkbox.isChecked(),
            logo_path=self._logo_path,
            logo_scale=self.logo_scale_slider.value() / 100.0,
            logo_white_bg=self.logo_white_bg_cb.isChecked(),
        ).normalized()

    def generate_qr(self, save_to_history: bool = True) -> Optional[GeneratedQRResult]:
        """Validate current inputs, generate QR code, update preview, and save to SQLite history."""
        self.validation_error_label.setVisible(False)
        fields = self.collect_current_fields()
        config = self.collect_customization_config()

        try:
            result = QRGenerator.generate_from_fields(
                qr_type=self._active_type,
                fields=fields,
                config=config,
            )
        except PayloadValidationError as exc:
            err_msg = self._i18n.get(exc.translation_key)
            self.validation_error_label.setText(err_msg)
            self.validation_error_label.setVisible(True)
            return None
        except Exception as exc:
            self.validation_error_label.setText(str(exc))
            self.validation_error_label.setVisible(True)
            return None

        self.preview_widget.set_qr_result(result)

        # Persist recent colors & last customization if enabled
        self._settings.add_recent_color(config.fg_color)
        self._settings.add_recent_color(config.bg_color)
        self.recent_colors_bar.set_colors(self._settings.get("recent_colors", []))
        if self._settings.get("remember_last_settings", True):
            self._settings.set("last_customization", config.to_dict())

        if save_to_history:
            self._history_repo.add_entry(
                qr_type=result.qr_type,
                title=result.title,
                payload=result.payload,
                fields=result.fields,
                customization=result.config.to_dict(),
            )
            self.history_updated.emit()

        return result

    def load_preset(
        self,
        qr_type: str,
        fields: Dict[str, Any],
        customization: Optional[Dict[str, Any]] = None,
        auto_generate: bool = False,
    ) -> None:
        """Populate form fields and customization settings from a template or history entry."""
        self.set_qr_type(qr_type)
        if qr_type == "url":
            self.url_input.setText(str(fields.get("url", "")))
            self.url_validate_cb.setChecked(bool(fields.get("strict_validate", True)))
        elif qr_type == "text":
            self.text_input.setPlainText(str(fields.get("text", "")))
        elif qr_type == "wifi":
            self.wifi_ssid_input.setText(str(fields.get("ssid", "")))
            self.wifi_pass_input.setText(str(fields.get("password", "")))
            sec = str(fields.get("security", "WPA"))
            idx = self.wifi_sec_combo.findData(sec)
            if idx >= 0:
                self.wifi_sec_combo.setCurrentIndex(idx)
            self.wifi_hidden_cb.setChecked(bool(fields.get("hidden", False)))
        elif qr_type == "email":
            self.email_to_input.setText(str(fields.get("recipient", "")))
            self.email_subj_input.setText(str(fields.get("subject", "")))
            self.email_msg_input.setPlainText(str(fields.get("message", "")))
        elif qr_type == "phone":
            self.phone_input.setText(str(fields.get("phone", "")))
        elif qr_type == "sms":
            self.sms_phone_input.setText(str(fields.get("phone", "")))
            self.sms_msg_input.setPlainText(str(fields.get("message", "")))
        elif qr_type == "vcard":
            self.vcard_fn_input.setText(str(fields.get("first_name", "")))
            self.vcard_ln_input.setText(str(fields.get("last_name", "")))
            self.vcard_phone_input.setText(str(fields.get("phone", "")))
            self.vcard_email_input.setText(str(fields.get("email", "")))
            self.vcard_org_input.setText(str(fields.get("organization", "")))
            self.vcard_web_input.setText(str(fields.get("website", "")))

        if customization:
            cfg = QRCustomizationConfig.from_dict(customization)
            self.fg_picker.set_color(cfg.fg_color, emit_signal=False)
            self.bg_picker.set_color(cfg.bg_color, emit_signal=False)
            self.set_qr_style(cfg.style)
            ecc_idx = self.ecc_combo.findData(cfg.error_correction)
            if ecc_idx >= 0:
                self.ecc_combo.setCurrentIndex(ecc_idx)
            sz_idx = self.size_combo.findData(cfg.size)
            if sz_idx >= 0:
                self.size_combo.setCurrentIndex(sz_idx)
            else:
                self.size_combo.setCurrentIndex(self.size_combo.findData("custom"))
                self.custom_size_spin.setValue(cfg.size)
            if cfg.logo_path and Path(cfg.logo_path).exists():
                self._set_logo_path(cfg.logo_path)
            else:
                self._remove_logo()
            self.logo_scale_slider.setValue(int(round(cfg.logo_scale * 100)))
            self.logo_white_bg_cb.setChecked(cfg.logo_white_bg)
            self._check_color_contrast()

        if auto_generate:
            self.generate_qr(save_to_history=False)

    def clear_current_form(self) -> None:
        """Clear fields in the currently active form."""
        self.validation_error_label.setVisible(False)
        qt = self._active_type
        if qt == "url":
            self.url_input.clear()
        elif qt == "text":
            self.text_input.clear()
        elif qt == "wifi":
            self.wifi_ssid_input.clear()
            self.wifi_pass_input.clear()
            self.wifi_hidden_cb.setChecked(False)
        elif qt == "email":
            self.email_to_input.clear()
            self.email_subj_input.clear()
            self.email_msg_input.clear()
        elif qt == "phone":
            self.phone_input.clear()
        elif qt == "sms":
            self.sms_phone_input.clear()
            self.sms_msg_input.clear()
        elif qt == "vcard":
            self.vcard_fn_input.clear()
            self.vcard_ln_input.clear()
            self.vcard_phone_input.clear()
            self.vcard_email_input.clear()
            self.vcard_org_input.clear()
            self.vcard_web_input.clear()

    def _update_text_char_counter(self) -> None:
        current_text = self.text_input.toPlainText()
        if len(current_text) > self.MAX_TEXT_LENGTH:
            self.text_input.blockSignals(True)
            self.text_input.setPlainText(current_text[: self.MAX_TEXT_LENGTH])
            cursor = self.text_input.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.text_input.setTextCursor(cursor)
            self.text_input.blockSignals(False)
            current_text = self.text_input.toPlainText()
        self.text_char_label.setText(
            self._i18n.get("generator.text_char_count", count=len(current_text), max=self.MAX_TEXT_LENGTH)
        )

    def _toggle_wifi_password(self) -> None:
        is_hidden = self.wifi_pass_input.echoMode() == QLineEdit.EchoMode.Password
        self.wifi_pass_input.setEchoMode(
            QLineEdit.EchoMode.Normal if is_hidden else QLineEdit.EchoMode.Password
        )
        self._update_wifi_toggle_text()

    def _update_wifi_toggle_text(self) -> None:
        is_hidden = self.wifi_pass_input.echoMode() == QLineEdit.EchoMode.Password
        key = "generator.wifi_show_password" if is_hidden else "generator.wifi_hide_password"
        self.wifi_toggle_pass_btn.setText(self._i18n.get(key))

    def _on_wifi_security_changed(self) -> None:
        is_open = self.wifi_sec_combo.currentData() == "nopass"
        self.wifi_pass_input.setEnabled(not is_open)
        if is_open:
            self.wifi_pass_input.clear()

    def _on_color_changed(self, _hex: str) -> None:
        self._check_color_contrast()

    def _check_color_contrast(self) -> None:
        ratio = compute_contrast_ratio(self.fg_picker.color, self.bg_picker.color)
        self.contrast_warning_label.setVisible(ratio < 3.0)

    def _reset_colors(self) -> None:
        self.fg_picker.reset_to_default(emit_signal=False)
        self.bg_picker.reset_to_default(emit_signal=False)
        self._check_color_contrast()

    def _on_recent_swatch_clicked(self, hex_color: str) -> None:
        self.fg_picker.set_color(hex_color, emit_signal=True)

    def _on_size_combo_changed(self) -> None:
        is_custom = self.size_combo.currentData() == "custom"
        self.custom_size_container.setVisible(is_custom)
        if not is_custom:
            val = int(self.size_combo.currentData() or 1024)
            self.preview_widget.export_size_spin.setValue(val)

    def _choose_logo_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._i18n.get("customization.logo_upload_btn"),
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg)",
        )
        if not file_path:
            return
        try:
            with Image.open(file_path) as img:
                img.verify()
        except Exception:
            self.notification_requested.emit(
                self._i18n.get("validation.invalid_logo"),
                "error",
                "",
                None,
            )
            return
        self._set_logo_path(file_path)

    def _set_logo_path(self, file_path: str) -> None:
        self._logo_path = file_path
        self.logo_file_label.setText(Path(file_path).name)
        self.logo_remove_btn.setVisible(True)
        self.logo_warning_label.setVisible(True)
        # Automatically set Error Correction to H (30%) when a logo is enabled
        h_idx = self.ecc_combo.findData("H")
        if h_idx >= 0:
            self.ecc_combo.setCurrentIndex(h_idx)

    def _remove_logo(self) -> None:
        self._logo_path = None
        self.logo_file_label.setText(self._i18n.get("customization.logo_no_file"))
        self.logo_remove_btn.setVisible(False)
        self.logo_warning_label.setVisible(False)

    def _update_logo_scale_label(self) -> None:
        self.logo_scale_label.setText(
            self._i18n.get("customization.logo_size_label", percent=self.logo_scale_slider.value())
        )

    def _on_export_requested(self, fmt: str, size: int, transparent_bg: bool) -> None:
        result = self.preview_widget.current_result
        if result is None:
            self.notification_requested.emit(
                self._i18n.get("export.error_no_qr"),
                "error",
                "",
                None,
            )
            return

        default_dir = Path(str(self._settings.get("default_export_directory") or Path.home()))
        if not default_dir.exists():
            default_dir = Path.home()
        default_name = get_default_export_filename(fmt)
        initial_path = str(default_dir / default_name)

        filter_map = {
            "PNG": "PNG Image (*.png)",
            "JPG": "JPEG Image (*.jpg *.jpeg)",
            "SVG": "SVG Vector (*.svg)",
        }
        chosen_path, _ = QFileDialog.getSaveFileName(
            self,
            self._i18n.get("export.dialog_title"),
            initial_path,
            filter_map.get(fmt.upper(), "All Files (*.*)"),
        )
        if not chosen_path:
            return

        try:
            saved_path = QRExporter.export(
                qr_result=result,
                output_path=chosen_path,
                fmt=fmt,
                size=size,
                transparent_bg=transparent_bg,
            )
            folder = str(saved_path.parent)
            self.preview_widget.show_open_folder_button(folder)
            self.notification_requested.emit(
                self._i18n.get("export.success_message", filename=saved_path.name),
                "success",
                self._i18n.get("export.open_folder_action"),
                lambda f=folder: open_directory_in_os(f),
            )
        except Exception as exc:
            self.notification_requested.emit(
                self._i18n.get("export.error_save_failed", error=str(exc)),
                "error",
                "",
                None,
            )

    def _on_copy_requested(self) -> None:
        self.notification_requested.emit(
            self._i18n.get("export.copied_message"),
            "success",
            "",
            None,
        )

    def _on_open_last_folder(self) -> None:
        folder = self.preview_widget.last_saved_folder
        if folder:
            open_directory_in_os(folder)
