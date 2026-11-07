"""Configuration constants and resource path resolution for QUBIC."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

APP_NAME: str = "QUBIC"
APP_SUBTITLE: str = "QR Code Studio"
APP_VERSION: str = "1.0.0"
DEVELOPER_NAME: str = "Kemorovv"
GITHUB_PROFILE_URL: str = "https://github.com/kemorovv"
SUGGESTED_REPO_NAME: str = "QUBIC"

# Window geometry constants
DEFAULT_WINDOW_WIDTH: int = 1200
DEFAULT_WINDOW_HEIGHT: int = 780
MIN_WINDOW_WIDTH: int = 950
MIN_WINDOW_HEIGHT: int = 650

# Color Palette (Brand Specification)
COLOR_PALETTE: Dict[str, str] = {
    "bg_primary": "#101014",
    "bg_secondary": "#17171F",
    "bg_card": "#1D1C27",
    "accent_primary": "#9565FF",
    "accent_secondary": "#B28AFF",
    "text_primary": "#F5F2FF",
    "text_secondary": "#9994AA",
    "border": "#302B3D",
    "success": "#65D6A0",
    "error": "#FF6B78",
}

# Supported QR Code Types
QR_TYPES: List[str] = [
    "url",
    "text",
    "wifi",
    "email",
    "phone",
    "sms",
    "vcard",
]

# Supported QR Module Styles
QR_STYLES: List[str] = [
    "classic",
    "rounded",
    "dots",
    "soft",
]

# Supported Error Correction Levels
ERROR_CORRECTION_LEVELS: Dict[str, int] = {
    "L": 7,
    "M": 15,
    "Q": 25,
    "H": 30,
}

# Standard Output Sizes
QR_OUTPUT_SIZES: List[int] = [256, 512, 1024, 2048]
MIN_CUSTOM_QR_SIZE: int = 128
MAX_CUSTOM_QR_SIZE: int = 4096

# Supported Export Formats
EXPORT_FORMATS: List[str] = ["PNG", "JPG", "SVG"]

# Default QR Colors
DEFAULT_FG_COLOR: str = "#000000"
DEFAULT_BG_COLOR: str = "#FFFFFF"

# Default Preset Swatches
PRESET_COLORS: List[str] = [
    "#000000",
    "#101014",
    "#9565FF",
    "#6C3CE9",
    "#2563EB",
    "#059669",
    "#D97706",
    "#E11D48",
    "#FFFFFF",
    "#F5F2FF",
]

# Preferred Fonts
PREFERRED_FONTS: Tuple[str, ...] = ("Inter", "Manrope", "Segoe UI", "Sans-Serif")


def get_base_path() -> Path:
    """Resolve base project path reliably in both source and PyInstaller frozen builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parent.parent


def get_resource_path(relative_path: str) -> Path:
    """Return an absolute Path to a bundled asset, style, or locale file."""
    base = get_base_path()
    return (base / relative_path).resolve()


def get_app_data_dir() -> Path:
    """Return the user's persistent local application data directory for QUBIC."""
    env_override = os.environ.get("QUBIC_DATA_DIR")
    if env_override:
        path = Path(env_override).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    if sys.platform == "win32":
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if appdata:
            path = Path(appdata) / APP_NAME
        else:
            path = Path.home() / f".{APP_NAME.lower()}"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            path = Path(xdg_data) / APP_NAME
        else:
            path = Path.home() / ".local" / "share" / APP_NAME

    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = get_base_path() / "user_data"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_default_export_dir() -> Path:
    """Return a sensible default export directory (Pictures or user home)."""
    pictures = Path.home() / "Pictures"
    if pictures.exists() and pictures.is_dir():
        return pictures
    return Path.home()
