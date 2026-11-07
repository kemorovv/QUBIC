"""Persistent settings service for QUBIC."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.config import (
    DEFAULT_BG_COLOR,
    DEFAULT_FG_COLOR,
    PRESET_COLORS,
    get_app_data_dir,
    get_default_export_dir,
    get_resource_path,
)


DEFAULT_SETTINGS: Dict[str, Any] = {
    "language": "en",
    "theme": "dark",
    "default_export_format": "PNG",
    "default_qr_size": 1024,
    "default_error_correction": "M",
    "default_export_directory": "",
    "remember_last_settings": True,
    "recent_colors": list(PRESET_COLORS[:8]),
    "last_customization": {
        "fg_color": DEFAULT_FG_COLOR,
        "bg_color": DEFAULT_BG_COLOR,
        "style": "classic",
        "error_correction": "M",
        "size": 1024,
        "transparent_bg": False,
    },
}


class SettingsService:
    """Manages persistent user settings stored in JSON format."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        if settings_path is not None:
            self._settings_path = settings_path
        else:
            self._settings_path = get_app_data_dir() / "config.json"
        self._data: Dict[str, Any] = copy.deepcopy(DEFAULT_SETTINGS)
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self.load()

    @property
    def settings_path(self) -> Path:
        """Return the active settings file path."""
        return self._settings_path

    def load(self) -> Dict[str, Any]:
        """Load settings from user data directory, falling back to bundled config.json or defaults."""
        base_defaults = copy.deepcopy(DEFAULT_SETTINGS)
        bundled_cfg = get_resource_path("config.json")
        if bundled_cfg.exists():
            try:
                with open(bundled_cfg, "r", encoding="utf-8") as fh:
                    bundled_data = json.load(fh)
                if isinstance(bundled_data, dict):
                    base_defaults.update(bundled_data)
            except (OSError, json.JSONDecodeError):
                pass

        if self._settings_path.exists():
            try:
                with open(self._settings_path, "r", encoding="utf-8") as fh:
                    user_data = json.load(fh)
                if isinstance(user_data, dict):
                    for key, val in user_data.items():
                        if key == "last_customization" and isinstance(val, dict):
                            merged_cust = copy.deepcopy(base_defaults["last_customization"])
                            merged_cust.update(val)
                            base_defaults["last_customization"] = merged_cust
                        else:
                            base_defaults[key] = val
            except (OSError, json.JSONDecodeError):
                pass

        if not base_defaults.get("default_export_directory"):
            base_defaults["default_export_directory"] = str(get_default_export_dir())

        self._data = base_defaults
        self.save(notify=False)
        return copy.deepcopy(self._data)

    def save(self, notify: bool = True) -> None:
        """Persist current settings to disk."""
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._settings_path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
        except OSError:
            pass
        if notify:
            for callback in list(self._listeners):
                callback(copy.deepcopy(self._data))

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key."""
        return copy.deepcopy(self._data.get(key, default))

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Update a setting value and optionally save immediately."""
        self._data[key] = copy.deepcopy(value)
        if auto_save:
            self.save()

    def update(self, values: Dict[str, Any], auto_save: bool = True) -> None:
        """Batch update multiple settings keys."""
        for k, v in values.items():
            self._data[k] = copy.deepcopy(v)
        if auto_save:
            self.save()

    def add_recent_color(self, hex_color: str) -> List[str]:
        """Add a normalized HEX color to the front of recent_colors (up to 10 items)."""
        normalized = hex_color.strip().upper()
        if not normalized.startswith("#"):
            normalized = f"#{normalized}"
        recent: List[str] = [c.upper() for c in self._data.get("recent_colors", [])]
        if normalized in recent:
            recent.remove(normalized)
        recent.insert(0, normalized)
        recent = recent[:10]
        self._data["recent_colors"] = recent
        self.save(notify=False)
        return list(recent)

    def reset_to_defaults(self) -> Dict[str, Any]:
        """Reset all settings to factory defaults and persist."""
        self._data = copy.deepcopy(DEFAULT_SETTINGS)
        self._data["default_export_directory"] = str(get_default_export_dir())
        self.save(notify=True)
        return copy.deepcopy(self._data)

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to settings changes."""
        if callback not in self._listeners:
            self._listeners.append(callback)
