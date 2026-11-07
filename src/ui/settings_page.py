"""Settings Page for appearance, live language switching, export defaults, and data management."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.config import EXPORT_FORMATS, QR_OUTPUT_SIZES, get_app_data_dir
from src.database.history_repository import HistoryRepository
from src.services.localization import get_i18n
from src.services.settings_service import SettingsService
from src.ui.generator_page import open_directory_in_os
from src.widgets.custom_button import CustomButton


class SettingsPage(QWidget):
    """Allows configuring theme, language, default export behavior, and local data."""

    theme_changed = Signal(str)
    history_cleared = Signal()
    notification_requested = Signal(str, str, str, object)

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
        self._updating_controls: bool = False

        self._setup_ui()
        self._load_values_from_settings()
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

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(16)

        # Appearance & Language Card
        app_card = QFrame()
        app_card.setObjectName("Card")
        app_layout = QVBoxLayout(app_card)
        app_layout.setContentsMargins(20, 18, 20, 18)
        app_layout.setSpacing(12)

        self.appearance_title = QLabel()
        self.appearance_title.setObjectName("SectionTitle")
        app_layout.addWidget(self.appearance_title)

        row_theme_lang = QHBoxLayout()
        row_theme_lang.setSpacing(16)

        theme_col = QVBoxLayout()
        self.theme_label = QLabel()
        self.theme_label.setObjectName("FieldLabel")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("", "dark")
        self.theme_combo.addItem("", "light")
        self.theme_combo.addItem("", "system")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_col.addWidget(self.theme_label)
        theme_col.addWidget(self.theme_combo)
        row_theme_lang.addLayout(theme_col, 1)

        lang_col = QVBoxLayout()
        self.lang_label = QLabel()
        self.lang_label.setObjectName("FieldLabel")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("", "en")
        self.lang_combo.addItem("", "ru")
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_col.addWidget(self.lang_label)
        lang_col.addWidget(self.lang_combo)
        row_theme_lang.addLayout(lang_col, 1)

        app_layout.addLayout(row_theme_lang)
        layout.addWidget(app_card)

        # General Defaults Card
        gen_card = QFrame()
        gen_card.setObjectName("Card")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(20, 18, 20, 18)
        gen_layout.setSpacing(12)

        self.general_title = QLabel()
        self.general_title.setObjectName("SectionTitle")
        gen_layout.addWidget(self.general_title)

        defaults_row = QHBoxLayout()
        defaults_row.setSpacing(14)

        fmt_col = QVBoxLayout()
        self.def_fmt_label = QLabel()
        self.def_fmt_label.setObjectName("FieldLabel")
        self.def_fmt_combo = QComboBox()
        for fmt in EXPORT_FORMATS:
            self.def_fmt_combo.addItem(fmt, fmt)
        self.def_fmt_combo.currentIndexChanged.connect(self._save_general_settings)
        fmt_col.addWidget(self.def_fmt_label)
        fmt_col.addWidget(self.def_fmt_combo)
        defaults_row.addLayout(fmt_col, 1)

        sz_col = QVBoxLayout()
        self.def_size_label = QLabel()
        self.def_size_label.setObjectName("FieldLabel")
        self.def_size_combo = QComboBox()
        for sz in QR_OUTPUT_SIZES:
            self.def_size_combo.addItem(f"{sz} × {sz} px", sz)
        self.def_size_combo.currentIndexChanged.connect(self._save_general_settings)
        sz_col.addWidget(self.def_size_label)
        sz_col.addWidget(self.def_size_combo)
        defaults_row.addLayout(sz_col, 1)

        ecc_col = QVBoxLayout()
        self.def_ecc_label = QLabel()
        self.def_ecc_label.setObjectName("FieldLabel")
        self.def_ecc_combo = QComboBox()
        for code in ("L", "M", "Q", "H"):
            self.def_ecc_combo.addItem(code, code)
        self.def_ecc_combo.currentIndexChanged.connect(self._save_general_settings)
        ecc_col.addWidget(self.def_ecc_label)
        ecc_col.addWidget(self.def_ecc_combo)
        defaults_row.addLayout(ecc_col, 1)

        gen_layout.addLayout(defaults_row)

        self.def_dir_label = QLabel()
        self.def_dir_label.setObjectName("FieldLabel")
        gen_layout.addWidget(self.def_dir_label)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self.def_dir_input = QLineEdit()
        self.def_dir_input.setReadOnly(True)
        self.browse_dir_btn = CustomButton("", variant="secondary")
        self.browse_dir_btn.clicked.connect(self._browse_export_dir)
        dir_row.addWidget(self.def_dir_input, 1)
        dir_row.addWidget(self.browse_dir_btn)
        gen_layout.addLayout(dir_row)

        self.remember_last_cb = QCheckBox()
        self.remember_last_cb.toggled.connect(self._save_general_settings)
        gen_layout.addWidget(self.remember_last_cb)

        layout.addWidget(gen_card)

        # Data Management Card
        data_card = QFrame()
        data_card.setObjectName("Card")
        data_layout = QVBoxLayout(data_card)
        data_layout.setContentsMargins(20, 18, 20, 18)
        data_layout.setSpacing(12)

        self.data_title = QLabel()
        self.data_title.setObjectName("SectionTitle")
        data_layout.addWidget(self.data_title)

        data_btn_row = QHBoxLayout()
        data_btn_row.setSpacing(10)

        self.open_data_btn = CustomButton("", variant="secondary")
        self.open_data_btn.clicked.connect(lambda: open_directory_in_os(str(get_app_data_dir())))
        data_btn_row.addWidget(self.open_data_btn)

        self.clear_history_btn = CustomButton("", variant="danger")
        self.clear_history_btn.clicked.connect(self._confirm_clear_history)
        data_btn_row.addWidget(self.clear_history_btn)

        self.reset_settings_btn = CustomButton("", variant="danger")
        self.reset_settings_btn.clicked.connect(self._confirm_reset_settings)
        data_btn_row.addWidget(self.reset_settings_btn)

        data_btn_row.addStretch(1)
        data_layout.addLayout(data_btn_row)
        layout.addWidget(data_card)

        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        t = self._i18n.get
        self.page_title.setText(t("settings.title"))
        self.page_subtitle.setText(t("settings.subtitle"))
        self.appearance_title.setText(t("settings.appearance_section"))
        self.theme_label.setText(t("settings.theme_label"))
        self.theme_combo.setItemText(0, t("settings.theme_dark"))
        self.theme_combo.setItemText(1, t("settings.theme_light"))
        self.theme_combo.setItemText(2, t("settings.theme_system"))

        self.lang_label.setText(t("settings.language_label"))
        self.lang_combo.setItemText(0, t("settings.lang_en"))
        self.lang_combo.setItemText(1, t("settings.lang_ru"))

        self.general_title.setText(t("settings.general_section"))
        self.def_fmt_label.setText(t("settings.default_format_label"))
        self.def_size_label.setText(t("settings.default_size_label"))
        self.def_ecc_label.setText(t("settings.default_ecc_label"))
        self.def_ecc_combo.setItemText(0, t("customization.ecc_l"))
        self.def_ecc_combo.setItemText(1, t("customization.ecc_m"))
        self.def_ecc_combo.setItemText(2, t("customization.ecc_q"))
        self.def_ecc_combo.setItemText(3, t("customization.ecc_h"))

        self.def_dir_label.setText(t("settings.default_dir_label"))
        self.browse_dir_btn.setText(t("settings.browse_dir_btn"))
        self.remember_last_cb.setText(t("settings.remember_last_checkbox"))

        self.data_title.setText(t("settings.data_section"))
        self.open_data_btn.setText(t("settings.open_data_dir_btn"))
        self.clear_history_btn.setText(t("settings.clear_history_btn"))
        self.reset_settings_btn.setText(t("settings.reset_settings_btn"))

    def _load_values_from_settings(self) -> None:
        self._updating_controls = True
        try:
            theme = str(self._settings.get("theme", "dark"))
            t_idx = self.theme_combo.findData(theme)
            if t_idx >= 0:
                self.theme_combo.setCurrentIndex(t_idx)

            lang = str(self._settings.get("language", "en"))
            l_idx = self.lang_combo.findData(lang)
            if l_idx >= 0:
                self.lang_combo.setCurrentIndex(l_idx)

            fmt = str(self._settings.get("default_export_format", "PNG"))
            f_idx = self.def_fmt_combo.findData(fmt)
            if f_idx >= 0:
                self.def_fmt_combo.setCurrentIndex(f_idx)

            sz = int(self._settings.get("default_qr_size", 1024))
            s_idx = self.def_size_combo.findData(sz)
            if s_idx >= 0:
                self.def_size_combo.setCurrentIndex(s_idx)

            ecc = str(self._settings.get("default_error_correction", "M"))
            e_idx = self.def_ecc_combo.findData(ecc)
            if e_idx >= 0:
                self.def_ecc_combo.setCurrentIndex(e_idx)

            self.def_dir_input.setText(str(self._settings.get("default_export_directory", "")))
            self.remember_last_cb.setChecked(bool(self._settings.get("remember_last_settings", True)))
        finally:
            self._updating_controls = False

    def _on_theme_changed(self) -> None:
        if self._updating_controls:
            return
        theme = str(self.theme_combo.currentData() or "dark")
        self._settings.set("theme", theme)
        self.theme_changed.emit(theme)

    def _on_language_changed(self) -> None:
        if self._updating_controls:
            return
        lang = str(self.lang_combo.currentData() or "en")
        self._settings.set("language", lang)
        self._i18n.set_language(lang)

    def _save_general_settings(self) -> None:
        if self._updating_controls:
            return
        self._settings.update(
            {
                "default_export_format": str(self.def_fmt_combo.currentData() or "PNG"),
                "default_qr_size": int(self.def_size_combo.currentData() or 1024),
                "default_error_correction": str(self.def_ecc_combo.currentData() or "M"),
                "remember_last_settings": bool(self.remember_last_cb.isChecked()),
            }
        )

    def _browse_export_dir(self) -> None:
        current = self.def_dir_input.text() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(
            self,
            self._i18n.get("settings.default_dir_label"),
            current,
        )
        if chosen:
            self.def_dir_input.setText(chosen)
            self._settings.set("default_export_directory", chosen)

    def _confirm_clear_history(self) -> None:
        reply = QMessageBox.question(
            self,
            self._i18n.get("history.confirm_clear_title"),
            self._i18n.get("history.confirm_clear_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._history_repo.clear_all()
            self.history_cleared.emit()
            self.notification_requested.emit(
                self._i18n.get("history.cleared_notification"),
                "success",
                "",
                None,
            )

    def _confirm_reset_settings(self) -> None:
        reply = QMessageBox.question(
            self,
            self._i18n.get("settings.reset_confirm_title"),
            self._i18n.get("settings.reset_confirm_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._settings.reset_to_defaults()
            self._load_values_from_settings()
            self._i18n.set_language(str(self._settings.get("language", "en")))
            self.theme_changed.emit(str(self._settings.get("theme", "dark")))
            self.notification_requested.emit(
                self._i18n.get("settings.reset_notification"),
                "success",
                "",
                None,
            )
