"""Automated tests for English and Russian localization parity and settings persistence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.services.localization import LocalizationService
from src.services.settings_service import SettingsService


class TestLocalizationAndSettings(unittest.TestCase):
    """Verifies complete translation coverage for English and Russian and settings persistence."""

    def test_en_and_ru_key_parity_and_non_empty_values(self) -> None:
        i18n = LocalizationService(default_lang="en")
        en_keys = set(i18n.get_all_keys("en"))
        ru_keys = set(i18n.get_all_keys("ru"))

        self.assertGreater(len(en_keys), 100)
        self.assertEqual(
            en_keys,
            ru_keys,
            f"Key mismatch between en.json and ru.json: {en_keys ^ ru_keys}",
        )

        for key in en_keys:
            i18n.set_language("en")
            en_val = i18n.get(key)
            self.assertTrue(en_val.strip(), f"Empty English translation for {key}")

            i18n.set_language("ru")
            ru_val = i18n.get(key)
            self.assertTrue(ru_val.strip(), f"Empty Russian translation for {key}")

    def test_dynamic_language_switching_and_placeholders(self) -> None:
        i18n = LocalizationService(default_lang="en")
        notified_langs = []
        i18n.subscribe(lambda lang: notified_langs.append(lang))

        self.assertEqual(i18n.get("nav.generator"), "Generator")
        i18n.set_language("ru")
        self.assertEqual(i18n.get("nav.generator"), "Генератор")
        self.assertEqual(notified_langs, ["ru"])

        formatted = i18n.get("generator.text_char_count", count=42, max=2000)
        self.assertIn("42", formatted)
        self.assertIn("2000", formatted)

    def test_settings_persistence_and_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "config.json"
            svc = SettingsService(settings_path=cfg_path)
            self.assertEqual(svc.get("theme"), "dark")
            self.assertEqual(svc.get("language"), "en")

            svc.set("theme", "light")
            svc.set("language", "ru")
            svc.add_recent_color("#123456")

            # Reload from disk in a new SettingsService instance
            svc2 = SettingsService(settings_path=cfg_path)
            self.assertEqual(svc2.get("theme"), "light")
            self.assertEqual(svc2.get("language"), "ru")
            self.assertEqual(svc2.get("recent_colors")[0], "#123456")

            svc2.reset_to_defaults()
            self.assertEqual(svc2.get("theme"), "dark")
            self.assertEqual(svc2.get("language"), "en")


if __name__ == "__main__":
    unittest.main()
