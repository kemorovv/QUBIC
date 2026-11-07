"""Automated tests for all 7 QR payload builders and input validators."""

from __future__ import annotations

import unittest

from src.core.qr_payloads import (
    PayloadValidationError,
    build_email_payload,
    build_payload_from_fields,
    build_phone_payload,
    build_sms_payload,
    build_text_payload,
    build_url_payload,
    build_vcard_payload,
    build_wifi_payload,
)


class TestQRPayloads(unittest.TestCase):
    """Test suite for QR payload construction and validation."""

    def test_url_payload_auto_https(self) -> None:
        res = build_url_payload("github.com/kemorovv", strict_validate=True)
        self.assertEqual(res.qr_type, "url")
        self.assertEqual(res.payload, "https://github.com/kemorovv")

    def test_url_payload_preserves_http_and_https(self) -> None:
        res = build_url_payload("http://example.org/test?x=1", strict_validate=True)
        self.assertEqual(res.payload, "http://example.org/test?x=1")

    def test_url_payload_validation_errors(self) -> None:
        with self.assertRaises(PayloadValidationError) as ctx:
            build_url_payload("   ")
        self.assertEqual(ctx.exception.translation_key, "validation.empty_url")

        with self.assertRaises(PayloadValidationError) as ctx2:
            build_url_payload("not a valid url", strict_validate=True)
        self.assertEqual(ctx2.exception.translation_key, "validation.invalid_url")

    def test_text_payload_and_validation(self) -> None:
        res = build_text_payload("Hello QUBIC!\nSecond line.")
        self.assertEqual(res.qr_type, "text")
        self.assertEqual(res.payload, "Hello QUBIC!\nSecond line.")

        with self.assertRaises(PayloadValidationError) as ctx:
            build_text_payload("")
        self.assertEqual(ctx.exception.translation_key, "validation.empty_text")

    def test_wifi_payload_wpa_and_escaping(self) -> None:
        res = build_wifi_payload(
            ssid="My;Home:Net",
            password="Secret\\Pass;1",
            security="WPA",
            hidden=True,
        )
        self.assertEqual(res.qr_type, "wifi")
        self.assertEqual(
            res.payload,
            "WIFI:T:WPA;S:My\\;Home\\:Net;P:Secret\\\\Pass\\;1;H:true;;",
        )

    def test_wifi_payload_open_network(self) -> None:
        res = build_wifi_payload(ssid="CafeFreeWiFi", password="", security="nopass", hidden=False)
        self.assertEqual(res.payload, "WIFI:T:nopass;S:CafeFreeWiFi;;")

    def test_wifi_validation_errors(self) -> None:
        with self.assertRaises(PayloadValidationError) as ctx:
            build_wifi_payload(ssid="", password="123", security="WPA")
        self.assertEqual(ctx.exception.translation_key, "validation.empty_ssid")

        with self.assertRaises(PayloadValidationError) as ctx2:
            build_wifi_payload(ssid="SecuredNet", password="", security="WPA")
        self.assertEqual(ctx2.exception.translation_key, "validation.empty_password_secured")

    def test_email_payload_and_validation(self) -> None:
        res = build_email_payload(
            recipient="user@example.com",
            subject="Hello World",
            message="Line 1",
        )
        self.assertEqual(res.qr_type, "email")
        self.assertEqual(res.payload, "mailto:user@example.com?subject=Hello%20World&body=Line%201")

        with self.assertRaises(PayloadValidationError):
            build_email_payload("invalid-email")

    def test_phone_payload_and_validation(self) -> None:
        res = build_phone_payload("+1 (555) 234-5678")
        self.assertEqual(res.qr_type, "phone")
        self.assertEqual(res.payload, "tel:+15552345678")

        with self.assertRaises(PayloadValidationError):
            build_phone_payload("abc-def")

    def test_sms_payload_with_and_without_message(self) -> None:
        res1 = build_sms_payload("+1 (555) 234-5678", "Call me back")
        self.assertEqual(res1.payload, "SMSTO:+15552345678:Call me back")

        res2 = build_sms_payload("+1 (555) 234-5678", "")
        self.assertEqual(res2.payload, "SMSTO:+15552345678")

    def test_vcard_payload_and_validation(self) -> None:
        res = build_payload_from_fields(
            "vcard",
            {
                "first_name": "Alex",
                "last_name": "Morgan",
                "phone": "+15559876543",
                "email": "alex@example.com",
                "organization": "QUBIC",
                "website": "example.com",
            },
        )
        self.assertEqual(res.qr_type, "vcard")
        self.assertIn("BEGIN:VCARD", res.payload)
        self.assertIn("VERSION:3.0", res.payload)
        self.assertIn("N:Morgan;Alex;;;", res.payload)
        self.assertIn("FN:Alex Morgan", res.payload)
        self.assertIn("ORG:QUBIC", res.payload)
        self.assertIn("TEL;TYPE=CELL:+15559876543", res.payload)
        self.assertIn("EMAIL:alex@example.com", res.payload)
        self.assertIn("URL:https://example.com", res.payload)
        self.assertIn("END:VCARD", res.payload)

        with self.assertRaises(PayloadValidationError) as ctx:
            build_vcard_payload(first_name="", last_name="")
        self.assertEqual(ctx.exception.translation_key, "validation.empty_vcard_name")


if __name__ == "__main__":
    unittest.main()
