"""History Page for searching, filtering, sorting, reloading, and deleting saved QR codes."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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

from src.config import QR_TYPES
from src.core.qr_exporter import QRExporter, get_default_export_filename
from src.core.qr_generator import QRCustomizationConfig, QRGenerator
from src.database.history_repository import HistoryEntry, HistoryRepository
from src.services.localization import get_i18n
from src.services.settings_service import SettingsService
from src.ui.generator_page import open_directory_in_os
from src.widgets.custom_button import CustomButton
from src.widgets.qr_preview import pil_image_to_qpixmap


class HistoryPage(QWidget):
    """Displays persistent SQLite QR code generation history with search, filter, and sort."""

    load_entry_requested = Signal(object)  # Emits HistoryEntry
    notification_requested = Signal(str, str, str, object)

    def __init__(
        self,
        history_repo: HistoryRepository,
        settings_service: SettingsService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._i18n = get_i18n()
        self._repo = history_repo
        self._settings = settings_service

        self._setup_ui()
        self._i18n.subscribe(self.retranslate_ui)
        self.retranslate_ui()
        self.refresh_history()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("PageSubtitle")
        title_col.addWidget(self.page_title)
        title_col.addWidget(self.page_subtitle)
        header_row.addLayout(title_col, 1)

        self.clear_all_btn = CustomButton("", variant="danger")
        self.clear_all_btn.clicked.connect(self._confirm_clear_all)
        header_row.addWidget(self.clear_all_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header_row)

        # Toolbar (Search, Type Filter, Sort Order)
        toolbar_card = QFrame()
        toolbar_card.setObjectName("Card")
        tb_layout = QHBoxLayout(toolbar_card)
        tb_layout.setContentsMargins(16, 12, 16, 12)
        tb_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(lambda _t: self.refresh_history())
        tb_layout.addWidget(self.search_input, 3)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("", "all")
        for qt in QR_TYPES:
            self.filter_combo.addItem(qt, qt)
        self.filter_combo.currentIndexChanged.connect(lambda _i: self.refresh_history())
        tb_layout.addWidget(self.filter_combo, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("", "newest")
        self.sort_combo.addItem("", "oldest")
        self.sort_combo.currentIndexChanged.connect(lambda _i: self.refresh_history())
        tb_layout.addWidget(self.sort_combo, 1)

        root.addWidget(toolbar_card)

        # Scrollable list of history cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 8, 0)
        self.list_layout.setSpacing(12)
        self.scroll_area.setWidget(self.list_container)
        root.addWidget(self.scroll_area, 1)

        # Empty State
        self.empty_card = QFrame()
        self.empty_card.setObjectName("Card")
        empty_layout = QVBoxLayout(self.empty_card)
        empty_layout.setContentsMargins(32, 48, 32, 48)
        empty_layout.setSpacing(8)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_title = QLabel()
        self.empty_title.setObjectName("SectionTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_subtitle = QLabel()
        self.empty_subtitle.setObjectName("HintLabel")
        self.empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_subtitle.setWordWrap(True)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_subtitle)
        root.addWidget(self.empty_card, 1)

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        t = self._i18n.get
        self.page_title.setText(t("history.title"))
        self.page_subtitle.setText(t("history.subtitle"))
        self.clear_all_btn.setText(t("history.clear_all_btn"))
        self.search_input.setPlaceholderText(t("history.search_placeholder"))

        self.filter_combo.setItemText(0, t("history.filter_all"))
        for idx, qt in enumerate(QR_TYPES, start=1):
            self.filter_combo.setItemText(idx, t(f"qr_types.{qt}"))

        self.sort_combo.setItemText(0, t("history.sort_newest"))
        self.sort_combo.setItemText(1, t("history.sort_oldest"))

        self.empty_title.setText(t("history.empty_title"))
        self.empty_subtitle.setText(t("history.empty_subtitle"))
        self.refresh_history()

    def refresh_history(self) -> None:
        """Query SQLite repository and rebuild the history cards list."""
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        search_q = self.search_input.text().strip()
        type_filter = str(self.filter_combo.currentData() or "all")
        sort_order = str(self.sort_combo.currentData() or "newest")

        entries: List[HistoryEntry] = self._repo.list_entries(
            search_query=search_q,
            qr_type=type_filter,
            sort_order=sort_order,
        )

        has_items = len(entries) > 0
        self.scroll_area.setVisible(has_items)
        self.empty_card.setVisible(not has_items)
        self.clear_all_btn.setEnabled(self._repo.count() > 0)

        for entry in entries:
            self.list_layout.addWidget(self._create_entry_card(entry))
        self.list_layout.addStretch(1)

    def _create_entry_card(self, entry: HistoryEntry) -> QFrame:
        card = QFrame()
        card.setObjectName("HistoryCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(16)

        # Thumbnail preview
        thumb_label = QLabel()
        thumb_label.setFixedSize(68, 68)
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            cfg = QRCustomizationConfig.from_dict(entry.customization)
            cfg.size = 160
            res = QRGenerator.generate_from_fields(entry.qr_type, entry.fields, cfg)
            pix = pil_image_to_qpixmap(res.image).scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            thumb_label.setPixmap(pix)
        except Exception:
            pass
        row.addWidget(thumb_label)

        # Details column
        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        type_badge = QLabel(self._i18n.get(f"qr_types.{entry.qr_type}"))
        type_badge.setObjectName("FieldLabel")
        type_badge.setStyleSheet("color: #B28AFF;")
        info_col.addWidget(type_badge)

        title_lbl = QLabel(entry.title)
        title_lbl.setObjectName("SectionTitle")
        info_col.addWidget(title_lbl)

        date_lbl = QLabel(self._i18n.get("history.created_at", date=entry.created_at))
        date_lbl.setObjectName("HintLabel")
        info_col.addWidget(date_lbl)

        row.addLayout(info_col, 1)

        # Action buttons
        btn_col = QHBoxLayout()
        btn_col.setSpacing(8)

        open_btn = CustomButton(self._i18n.get("history.open_in_generator_btn"), variant="primary")
        open_btn.clicked.connect(lambda _c=False, e=entry: self.load_entry_requested.emit(e))
        btn_col.addWidget(open_btn)

        export_btn = CustomButton(self._i18n.get("history.regenerate_btn"), variant="secondary")
        export_btn.clicked.connect(lambda _c=False, e=entry: self._quick_export_entry(e))
        btn_col.addWidget(export_btn)

        del_btn = CustomButton(self._i18n.get("history.delete_btn"), variant="danger")
        del_btn.clicked.connect(lambda _c=False, e=entry: self._delete_entry(e.id))
        btn_col.addWidget(del_btn)

        row.addLayout(btn_col)
        return card

    def _delete_entry(self, entry_id: int) -> None:
        self._repo.delete_entry(entry_id)
        self.refresh_history()
        self.notification_requested.emit(
            self._i18n.get("history.deleted_notification"),
            "info",
            "",
            None,
        )

    def _confirm_clear_all(self) -> None:
        reply = QMessageBox.question(
            self,
            self._i18n.get("history.confirm_clear_title"),
            self._i18n.get("history.confirm_clear_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._repo.clear_all()
            self.refresh_history()
            self.notification_requested.emit(
                self._i18n.get("history.cleared_notification"),
                "success",
                "",
                None,
            )

    def _quick_export_entry(self, entry: HistoryEntry) -> None:
        try:
            cfg = QRCustomizationConfig.from_dict(entry.customization)
            qr_res = QRGenerator.generate_from_fields(entry.qr_type, entry.fields, cfg)
        except Exception as exc:
            self.notification_requested.emit(str(exc), "error", "", None)
            return

        fmt = str(self._settings.get("default_export_format", "PNG"))
        default_dir = Path(str(self._settings.get("default_export_directory") or Path.home()))
        initial_path = str(default_dir / get_default_export_filename(fmt))

        chosen_path, _ = QFileDialog.getSaveFileName(
            self,
            self._i18n.get("export.dialog_title"),
            initial_path,
            "PNG Image (*.png);;JPEG Image (*.jpg);;SVG Vector (*.svg)",
        )
        if not chosen_path:
            return

        ext = Path(chosen_path).suffix.lstrip(".").upper() or fmt
        saved = QRExporter.export(qr_res, chosen_path, fmt=ext, size=cfg.size)
        folder = str(saved.parent)
        self.notification_requested.emit(
            self._i18n.get("export.success_message", filename=saved.name),
            "success",
            self._i18n.get("export.open_folder_action"),
            lambda f=folder: open_directory_in_os(f),
        )
