"""Automated tests for QR code generation, styling, logo integration, decoding, and SQLite history."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.config import get_resource_path
from src.core.image_processor import (
    compute_contrast_ratio,
    normalize_hex_color,
    validate_hex_color,
)
from src.core.qr_generator import QRCustomizationConfig, QRGenerator
from src.database.database import DatabaseManager
from src.database.history_repository import HistoryRepository

try:
    import cv2

    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class TestQRGeneratorAndHistory(unittest.TestCase):
    """Tests QR generation, visual styles, logo integration, decoder readability, and history persistence."""

    @staticmethod
    def _decode_pil_image(img) -> str:
        if not HAS_CV2:
            return ""
        detector = cv2.QRCodeDetector()
        rgb = np.array(img.convert("RGB"))
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        decoded, _, _ = detector.detectAndDecode(bgr)
        return decoded

    def test_hex_color_validation_and_contrast(self) -> None:
        self.assertTrue(validate_hex_color("#9565FF"))
        self.assertTrue(validate_hex_color("fff"))
        self.assertFalse(validate_hex_color("#12345G"))
        self.assertEqual(normalize_hex_color("abc"), "#AABBCC")
        self.assertGreater(compute_contrast_ratio("#000000", "#FFFFFF"), 20.0)
        self.assertAlmostEqual(compute_contrast_ratio("#9565FF", "#9565FF"), 1.0, places=2)

    def test_all_qr_types_generate_and_decode(self) -> None:
        samples = [
            ("url", {"url": "https://github.com/kemorovv"}),
            ("text", {"text": "QUBIC Offline QR Code Studio 1.0.0"}),
            ("wifi", {"ssid": "OfficeNet", "password": "MyPassword123", "security": "WPA", "hidden": False}),
            ("email", {"recipient": "hello@example.com", "subject": "Inquiry", "message": "Test body"}),
            ("phone", {"phone": "+1 (555) 234-5678"}),
            ("sms", {"phone": "+1 (555) 234-5678", "message": "Quick SMS"}),
            (
                "vcard",
                {
                    "first_name": "Alex",
                    "last_name": "Morgan",
                    "phone": "+15559876543",
                    "email": "alex@example.com",
                    "organization": "QUBIC",
                    "website": "https://example.com",
                },
            ),
        ]
        for qtype, fields in samples:
            cfg = QRCustomizationConfig(size=512, style="classic", error_correction="M")
            res = QRGenerator.generate_from_fields(qtype, fields, cfg)
            self.assertEqual(res.image.size, (512, 512))
            if HAS_CV2:
                decoded = self._decode_pil_image(res.image)
                self.assertEqual(decoded, res.payload, f"Failed to decode {qtype}")

    def test_all_styles_and_ecc_levels_decode(self) -> None:
        for style in ("classic", "rounded", "dots", "soft"):
            for ecc in ("L", "M", "Q", "H"):
                cfg = QRCustomizationConfig(
                    fg_color="#101014",
                    bg_color="#FFFFFF",
                    style=style,
                    error_correction=ecc,
                    size=512,
                )
                res = QRGenerator.generate_from_fields(
                    "url", {"url": "https://github.com/kemorovv"}, cfg
                )
                if HAS_CV2:
                    decoded = self._decode_pil_image(res.image)
                    self.assertEqual(decoded, "https://github.com/kemorovv")

    def test_logo_integration_upgrades_ecc_and_decodes(self) -> None:
        icon_path = get_resource_path("assets/icon.png")
        self.assertTrue(icon_path.exists())
        cfg = QRCustomizationConfig(
            style="rounded",
            error_correction="L",  # Should auto-upgrade to H when logo_path is set
            size=512,
            logo_path=str(icon_path),
            logo_scale=0.18,
            logo_white_bg=True,
        ).normalized()
        self.assertEqual(cfg.error_correction, "H")

        res = QRGenerator.generate_from_fields(
            "url", {"url": "https://github.com/kemorovv"}, cfg
        )
        if HAS_CV2:
            decoded = self._decode_pil_image(res.image)
            self.assertEqual(decoded, "https://github.com/kemorovv")

    def test_sqlite_history_persistence_search_filter_sort_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            db = DatabaseManager(db_path=db_path)
            repo = HistoryRepository(db_manager=db)

            e1 = repo.add_entry(
                qr_type="url",
                title="https://github.com/kemorovv",
                payload="https://github.com/kemorovv",
                fields={"url": "https://github.com/kemorovv"},
                customization={"style": "classic"},
                created_at="2026-11-07 10:00:00",
            )
            e2 = repo.add_entry(
                qr_type="wifi",
                title="Wi-Fi: HomeNet",
                payload="WIFI:T:WPA;S:HomeNet;P:12345678;;",
                fields={"ssid": "HomeNet"},
                customization={"style": "rounded"},
                created_at="2026-11-07 11:00:00",
            )
            self.assertEqual(repo.count(), 2)

            # Re-open repository on same SQLite file to verify persistence across sessions
            repo2 = HistoryRepository(db_manager=DatabaseManager(db_path=db_path))
            newest = repo2.list_entries(sort_order="newest")
            self.assertEqual([x.id for x in newest], [e2.id, e1.id])

            oldest = repo2.list_entries(sort_order="oldest")
            self.assertEqual([x.id for x in oldest], [e1.id, e2.id])

            wifi_only = repo2.list_entries(qr_type="wifi")
            self.assertEqual(len(wifi_only), 1)
            self.assertEqual(wifi_only[0].title, "Wi-Fi: HomeNet")

            searched = repo2.list_entries(search_query="kemorovv")
            self.assertEqual(len(searched), 1)
            self.assertEqual(searched[0].id, e1.id)

            self.assertTrue(repo2.delete_entry(e1.id))
            self.assertEqual(repo2.count(), 1)

            repo2.clear_all()
            self.assertEqual(repo2.count(), 0)


if __name__ == "__main__":
    unittest.main()
