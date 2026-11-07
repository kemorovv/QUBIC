"""Automated tests for PNG, JPG, and SVG export functionality."""

from __future__ import annotations

import datetime
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from src.config import get_resource_path
from src.core.qr_exporter import QRExporter, get_default_export_filename
from src.core.qr_generator import QRCustomizationConfig, QRGenerator


class TestQRExporter(unittest.TestCase):
    """Test suite for PNG, JPG, and SVG QR code exporters."""

    def setUp(self) -> None:
        self.cfg = QRCustomizationConfig(
            fg_color="#9565FF",
            bg_color="#FFFFFF",
            style="rounded",
            error_correction="M",
            size=512,
        )
        self.qr_result = QRGenerator.generate_from_fields(
            "url",
            {"url": "https://github.com/kemorovv"},
            self.cfg,
        )

    def test_default_export_filename(self) -> None:
        fixed_date = datetime.datetime(2026, 11, 7, 12, 0, 0)
        self.assertEqual(
            get_default_export_filename("PNG", date_override=fixed_date),
            "qubic_qr_2026-11-07.png",
        )
        self.assertEqual(
            get_default_export_filename("SVG", date_override=fixed_date),
            "qubic_qr_2026-11-07.svg",
        )

    def test_export_png_opaque_and_transparent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p_opaque = Path(tmpdir) / "qr_opaque.png"
            QRExporter.export_png(self.qr_result, p_opaque, size=512, transparent_bg=False)
            self.assertTrue(p_opaque.exists())
            with Image.open(p_opaque) as im:
                self.assertEqual(im.size, (512, 512))
                self.assertEqual(im.getpixel((0, 0))[3], 255)

            p_trans = Path(tmpdir) / "qr_transparent.png"
            QRExporter.export_png(self.qr_result, p_trans, size=1024, transparent_bg=True)
            self.assertTrue(p_trans.exists())
            with Image.open(p_trans) as im_t:
                self.assertEqual(im_t.size, (1024, 1024))
                # Corner quiet zone pixel must be fully transparent (alpha == 0)
                self.assertEqual(im_t.getpixel((0, 0))[3], 0)

    def test_export_jpg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p_jpg = Path(tmpdir) / "qr_code.jpg"
            QRExporter.export_jpg(self.qr_result, p_jpg, size=512, bg_color="#F5F2FF")
            self.assertTrue(p_jpg.exists())
            with Image.open(p_jpg) as im:
                self.assertEqual(im.mode, "RGB")
                self.assertEqual(im.size, (512, 512))

    def test_export_svg_and_logo_embedding(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p_svg = Path(tmpdir) / "qr_vector.svg"
            icon_path = get_resource_path("assets/icon.png")
            cfg_logo = QRCustomizationConfig(
                fg_color="#101014",
                bg_color="#FFFFFF",
                style="dots",
                error_correction="H",
                size=1024,
                logo_path=str(icon_path),
            )
            res_logo = QRGenerator.generate_from_fields(
                "url", {"url": "https://github.com/kemorovv"}, cfg_logo
            )
            QRExporter.export_svg(res_logo, p_svg, size=1024, transparent_bg=False)
            self.assertTrue(p_svg.exists())

            svg_text = p_svg.read_text(encoding="utf-8")
            root = ET.fromstring(svg_text)
            self.assertTrue(root.tag.endswith("svg"))
            self.assertIn("circle", svg_text)
            self.assertIn("data:image/png;base64,", svg_text)


if __name__ == "__main__":
    unittest.main()
