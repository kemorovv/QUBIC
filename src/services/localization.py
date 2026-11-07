"""Centralized localization service supporting dynamic English and Russian switching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.config import get_resource_path


class LocalizationService:
    """Manages translations loaded from JSON files in locales/."""

    SUPPORTED_LANGUAGES: Dict[str, str] = {
        "en": "English",
        "ru": "Русский",
    }

    def __init__(self, default_lang: str = "en", locales_dir: Optional[Path] = None) -> None:
        self._locales_dir: Path = locales_dir or get_resource_path("locales")
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._current_lang: str = default_lang if default_lang in self.SUPPORTED_LANGUAGES else "en"
        self._listeners: List[Callable[[str], None]] = []
        self._load_all_locales()

    def _load_all_locales(self) -> None:
        """Load en.json and ru.json into memory."""
        for lang_code in self.SUPPORTED_LANGUAGES:
            file_path = self._locales_dir / f"{lang_code}.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as fh:
                    self._translations[lang_code] = json.load(fh)
            else:
                self._translations[lang_code] = {}

    @property
    def current_language(self) -> str:
        """Return currently active language code ('en' or 'ru')."""
        return self._current_lang

    def set_language(self, lang_code: str) -> None:
        """Switch active language and notify all subscribed UI components."""
        normalized = (lang_code or "en").strip().lower()
        if normalized not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language code: {lang_code}")
        if normalized == self._current_lang:
            return
        self._current_lang = normalized
        for callback in list(self._listeners):
            callback(self._current_lang)

    def subscribe(self, callback: Callable[[str], None]) -> None:
        """Register a listener function to be called whenever language changes."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        """Unregister a language change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def get(self, key: str, **kwargs: Any) -> str:
        """Look up a dot-separated translation key (e.g. 'generator.title') and format placeholders."""
        value = self._resolve_key(self._current_lang, key)
        if value is None and self._current_lang != "en":
            value = self._resolve_key("en", key)
        if value is None:
            return key
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value
        return str(value)

    def tr(self, key: str, **kwargs: Any) -> str:
        """Alias for get(key, **kwargs)."""
        return self.get(key, **kwargs)

    def get_all_keys(self, lang_code: Optional[str] = None) -> List[str]:
        """Return a flat list of all dot-separated keys for inspection and testing."""
        target = lang_code or self._current_lang
        data = self._translations.get(target, {})
        keys: List[str] = []

        def _walk(node: Dict[str, Any], prefix: str = "") -> None:
            for k, v in node.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    _walk(v, full_key)
                else:
                    keys.append(full_key)

        _walk(data)
        return sorted(keys)

    def _resolve_key(self, lang_code: str, key: str) -> Optional[Any]:
        parts = key.split(".")
        node: Any = self._translations.get(lang_code, {})
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return node


_global_i18n: Optional[LocalizationService] = None


def get_i18n() -> LocalizationService:
    """Return singleton LocalizationService instance."""
    global _global_i18n
    if _global_i18n is None:
        _global_i18n = LocalizationService()
    return _global_i18n


def tr(key: str, **kwargs: Any) -> str:
    """Convenience module-level translation lookup."""
    return get_i18n().get(key, **kwargs)
