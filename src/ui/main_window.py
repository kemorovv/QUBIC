"""Main Window orchestrating sidebar navigation, stacked pages, themes, and notifications."""

from __future__ import annotations

from typing import Callable, Dict, Optional

from PySide6.QtGui import QGuiApplication, QIcon, QPalette
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from src.config import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    get_resource_path,
)
from src.database.history_repository import HistoryEntry, HistoryRepository
from src.services.localization import get_i18n
from src.services.settings_service import SettingsService
from src.ui.about_page import AboutPage
from src.ui.generator_page import GeneratorPage
from src.ui.history_page import HistoryPage
from src.ui.settings_page import SettingsPage
from src.ui.sidebar import Sidebar
from src.ui.templates_page import TemplatePreset, TemplatesPage
from src.widgets.notification import NotificationBanner


class MainWindow(QMainWindow):
    """Primary desktop window for QUBIC — QR Code Studio."""

    def __init__(
        self,
        settings_service: Optional[SettingsService] = None,
        history_repo: Optional[HistoryRepository] = None,
    ) -> None:
        super().__init__()
        self.setObjectName("MainWindow")
        self._i18n = get_i18n()
        self._settings = settings_service or SettingsService()
        self._history_repo = history_repo or HistoryRepository()

        # Initialize active language from saved settings before building pages
        saved_lang = str(self._settings.get("language", "en"))
        if saved_lang in self._i18n.SUPPORTED_LANGUAGES:
            self._i18n.set_language(saved_lang)

        self._setup_window_properties()
        self._setup_ui()
        self.apply_theme(str(self._settings.get("theme", "dark")))

        self._i18n.subscribe(self.retranslate_ui)
        self.retranslate_ui()

    def _setup_window_properties(self) -> None:
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        icon_path = get_resource_path("assets/icon.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("MainWindow")
        self.setCentralWidget(central)

        main_row = QHBoxLayout(central)
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(0)

        self.sidebar = Sidebar(central)
        self.sidebar.navigation_Selected.connect(self.navigate_to)
        main_row.addWidget(self.sidebar)

        self.pages_stack = QStackedWidget(central)
        main_row.addWidget(self.pages_stack, 1)

        self.generator_page = GeneratorPage(self._settings, self._history_repo, self)
        self.history_page = HistoryPage(self._history_repo, self._settings, self)
        self.templates_page = TemplatesPage(self)
        self.settings_page = SettingsPage(self._settings, self._history_repo, self)
        self.about_page = AboutPage(self)

        self._page_map: Dict[str, QWidget] = {
            "generator": self.generator_page,
            "history": self.history_page,
            "templates": self.templates_page,
            "settings": self.settings_page,
            "about": self.about_page,
        }
        for page in self._page_map.values():
            self.pages_stack.addWidget(page)

        # Floating Toast Notification Banner
        self.toast = NotificationBanner(central)

        # Wire cross-page signals
        self.generator_page.notification_requested.connect(self.show_notification)
        self.generator_page.history_updated.connect(self.history_page.refresh_history)

        self.history_page.notification_requested.connect(self.show_notification)
        self.history_page.load_entry_requested.connect(self._on_load_history_entry)

        self.templates_page.template_selected.connect(self._on_use_template)

        self.settings_page.theme_changed.connect(self.apply_theme)
        self.settings_page.history_cleared.connect(self.history_page.refresh_history)
        self.settings_page.notification_requested.connect(self.show_notification)

    def retranslate_ui(self, _lang: Optional[str] = None) -> None:
        self.setWindowTitle(self._i18n.get("app.window_title"))

    def navigate_to(self, page_key: str) -> None:
        """Switch the main workspace to the requested section without reopening the window."""
        target = self._page_map.get(page_key)
        if target is None:
            return
        if page_key == "history":
            self.history_page.refresh_history()
        self.sidebar.set_active_page(page_key)
        self.pages_stack.setCurrentWidget(target)

    def apply_theme(self, theme_mode: str) -> None:
        """Load and apply either theme_dark.qss or theme_light.qss."""
        mode = (theme_mode or "dark").strip().lower()
        if mode == "system":
            palette = QGuiApplication.palette()
            win_color = palette.color(QPalette.ColorRole.Window)
            is_dark = win_color.lightness() < 128
            qss_name = "theme_dark.qss" if is_dark else "theme_light.qss"
        elif mode == "light":
            qss_name = "theme_light.qss"
        else:
            qss_name = "theme_dark.qss"

        qss_path = get_resource_path(f"src/styles/{qss_name}")
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as fh:
                self.setStyleSheet(fh.read())

    def show_notification(
        self,
        message: str,
        level: str = "success",
        action_text: str = "",
        action_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self.toast.show_message(
            message=message,
            level=level,
            action_text=action_text or None,
            action_callback=action_callback,
        )

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast.reposition()

    def _on_load_history_entry(self, entry: HistoryEntry) -> None:
        self.generator_page.load_preset(
            qr_type=entry.qr_type,
            fields=entry.fields,
            customization=entry.customization,
            auto_generate=True,
        )
        self.navigate_to("generator")
        self.show_notification(self._i18n.get("history.loaded_notification"), "success")

    def _on_use_template(self, preset: TemplatePreset, localized_name: str) -> None:
        self.generator_page.load_preset(
            qr_type=preset.qr_type,
            fields=preset.fields,
            customization=preset.customization,
            auto_generate=False,
        )
        self.navigate_to("generator")
        self.show_notification(
            self._i18n.get("templates.loaded_notification", name=localized_name),
            "success",
        )
