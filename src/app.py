"""Application bootstrap, high-DPI configuration, and QApplication initialization."""

from __future__ import annotations

import sys
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from src.config import APP_NAME, APP_VERSION, PREFERRED_FONTS, get_resource_path
from src.ui.main_window import MainWindow


def create_application(argv: Optional[List[str]] = None) -> QApplication:
    """Create and configure the QApplication instance for QUBIC."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(f"{APP_NAME} — QR Code Studio")
    app.setApplicationVersion(APP_VERSION)

    icon_path = get_resource_path("assets/icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    font = QFont(PREFERRED_FONTS[0], 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    return app


def run_app() -> int:
    """Launch the QUBIC desktop application and enter the Qt event loop."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("kemorovv.qubic.studio.1.0")
        except Exception:
            pass

    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
