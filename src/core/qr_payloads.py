"""Payload builders and validators for all 7 supported QR code types."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Tuple
from urllib.parse import quote


class PayloadValidationError(ValueError):
    """Exception raised when user input for a QR payload fails validation."""

    def __init__(self, translation_key: str, message: str = "") -> None:
        super().__init__(message or translation_key)
        self.translation_key = translation_key


@dataclass
class PayloadResult:
    """Encapsulates the formatted QR payload string and a human-readable summary title."""

    qr_type: str
    payload: str
    title: str
    fields: Dict[str, Any]


_URL_REGEX = re.compile(
    r"^(https?://)"
    r"(([A-Za-z0-9-]+\.)+[A-Za-z]{2,63}|localhost|\d{1,3}(\.\d{1,3}){3})"
    r"(:\d{1,5})?"
    r"(/[^\s]*)?$",
    re.IGNORECASE,
)

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_REGEX = re.compile(r"^\+?[\d\s().-]{3,30}$")


def normalize_url(raw_url: str, strict_validate: bool = True) -> str:
    """Normalize and optionally validate a website URL."""
    cleaned = (raw_url or "").strip()
    if not cleaned:
        raise PayloadValidationError("validation.empty_url", "URL cannot be empty.")

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        cleaned = f"https://{cleaned}"

    if strict_validate and not _URL_REGEX.match(cleaned):
        raise PayloadValidationError("validation.invalid_url", f"Invalid URL format: {cleaned}")

    return cleaned


def build_url_payload(url: str, strict_validate: bool = True) -> PayloadResult:
    """Build a URL QR payload."""
    normalized = normalize_url(url, strict_validate=strict_validate)
    return PayloadResult(
        qr_type="url",
        payload=normalized,
        title=normalized,
        fields={"url": normalized, "strict_validate": strict_validate},
    )


def build_text_payload(text: str) -> PayloadResult:
    """Build a Plain Text QR payload."""
    if not text or not text.strip():
        raise PayloadValidationError("validation.empty_text", "Text content cannot be empty.")
    cleaned = text.strip()
    first_line = cleaned.splitlines()[0][:60]
    title = first_line if len(cleaned) <= 60 else f"{first_line}..."
    return PayloadResult(
        qr_type="text",
        payload=cleaned,
        title=title,
        fields={"text": cleaned},
    )


def _escape_wifi_field(value: str) -> str:
    """Escape special characters in Wi-Fi QR fields according to ZXing specification."""
    escaped = value.replace("\\", "\\\\")
    for ch in (";", ",", ":", '"'):
        escaped = escaped.replace(ch, f"\\{ch}")
    return escaped


def build_wifi_payload(
    ssid: str,
    password: str = "",
    security: str = "WPA",
    hidden: bool = False,
) -> PayloadResult:
    """Build a standards-compliant Wi-Fi QR payload: WIFI:T:WPA;S:ssid;P:pass;H:true;;"""
    cleaned_ssid = (ssid or "").strip()
    if not cleaned_ssid:
        raise PayloadValidationError("validation.empty_ssid", "Wi-Fi SSID cannot be empty.")

    sec_norm = (security or "WPA").strip().upper()
    if sec_norm in ("OPEN", "NONE", "NOPASS", ""):
        sec_type = "nopass"
    elif sec_norm == "WEP":
        sec_type = "WEP"
    else:
        sec_type = "WPA"

    cleaned_password = password or ""
    if sec_type != "nopass" and not cleaned_password:
        raise PayloadValidationError(
            "validation.empty_password_secured",
            "Password is required for secured Wi-Fi networks.",
        )

    esc_ssid = _escape_wifi_field(cleaned_ssid)
    esc_pass = _escape_wifi_field(cleaned_password) if sec_type != "nopass" else ""
    parts = [f"WIFI:T:{sec_type};S:{esc_ssid};"]
    if sec_type != "nopass":
        parts.append(f"P:{esc_pass};")
    if hidden:
        parts.append("H:true;")
    parts.append(";")
    payload = "".join(parts)

    return PayloadResult(
        qr_type="wifi",
        payload=payload,
        title=f"Wi-Fi: {cleaned_ssid}",
        fields={
            "ssid": cleaned_ssid,
            "password": cleaned_password,
            "security": sec_type,
            "hidden": bool(hidden),
        },
    )


def build_email_payload(
    recipient: str,
    subject: str = "",
    message: str = "",
) -> PayloadResult:
    """Build a mailto: URI QR payload."""
    cleaned_recipient = (recipient or "").strip()
    if not cleaned_recipient:
        raise PayloadValidationError("validation.empty_email", "Recipient email cannot be empty.")
    if not _EMAIL_REGEX.match(cleaned_recipient):
        raise PayloadValidationError(
            "validation.invalid_email",
            f"Invalid email address: {cleaned_recipient}",
        )

    cleaned_subject = (subject or "").strip()
    cleaned_message = (message or "").strip()

    query_parts = []
    if cleaned_subject:
        query_parts.append(f"subject={quote(cleaned_subject)}")
    if cleaned_message:
        query_parts.append(f"body={quote(cleaned_message)}")

    if query_parts:
        payload = f"mailto:{cleaned_recipient}?{'&'.join(query_parts)}"
    else:
        payload = f"mailto:{cleaned_recipient}"

    return PayloadResult(
        qr_type="email",
        payload=payload,
        title=f"Email: {cleaned_recipient}",
        fields={
            "recipient": cleaned_recipient,
            "subject": cleaned_subject,
            "message": cleaned_message,
        },
    )


def _validate_and_clean_phone(phone: str) -> str:
    cleaned = (phone or "").strip()
    if not cleaned:
        raise PayloadValidationError("validation.empty_phone", "Phone number cannot be empty.")
    if not _PHONE_REGEX.match(cleaned) or not any(ch.isdigit() for ch in cleaned):
        raise PayloadValidationError("validation.invalid_phone", f"Invalid phone number: {cleaned}")
    # Keep leading '+' and digits for tel:/SMSTO: compatibility
    normalized = re.sub(r"[^\d+]", "", cleaned)
    return normalized


def build_phone_payload(phone: str) -> PayloadResult:
    """Build a tel: URI QR payload."""
    normalized = _validate_and_clean_phone(phone)
    return PayloadResult(
        qr_type="phone",
        payload=f"tel:{normalized}",
        title=f"Tel: {phone.strip()}",
        fields={"phone": phone.strip()},
    )


def build_sms_payload(phone: str, message: str = "") -> PayloadResult:
    """Build an SMSTO: QR payload."""
    normalized = _validate_and_clean_phone(phone)
    cleaned_msg = (message or "").strip()
    if cleaned_msg:
        payload = f"SMSTO:{normalized}:{cleaned_msg}"
    else:
        payload = f"SMSTO:{normalized}"
    return PayloadResult(
        qr_type="sms",
        payload=payload,
        title=f"SMS: {phone.strip()}",
        fields={"phone": phone.strip(), "message": cleaned_msg},
    )


def build_vcard_payload(
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
    email: str = "",
    organization: str = "",
    website: str = "",
) -> PayloadResult:
    """Build a standards-compliant vCard 3.0 QR payload."""
    fn = (first_name or "").strip()
    ln = (last_name or "").strip()
    if not fn and not ln:
        raise PayloadValidationError(
            "validation.empty_vcard_name",
            "At least a first name or last name is required for a Contact Card.",
        )

    cleaned_phone = (phone or "").strip()
    if cleaned_phone:
        _validate_and_clean_phone(cleaned_phone)

    cleaned_email = (email or "").strip()
    if cleaned_email and not _EMAIL_REGEX.match(cleaned_email):
        raise PayloadValidationError("validation.invalid_email", f"Invalid email: {cleaned_email}")

    cleaned_org = (organization or "").strip()
    cleaned_web = (website or "").strip()
    if cleaned_web:
        cleaned_web = normalize_url(cleaned_web, strict_validate=False)

    full_name = f"{fn} {ln}".strip()
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{ln};{fn};;;",
        f"FN:{full_name}",
    ]
    if cleaned_org:
        lines.append(f"ORG:{cleaned_org}")
    if cleaned_phone:
        lines.append(f"TEL;TYPE=CELL:{cleaned_phone}")
    if cleaned_email:
        lines.append(f"EMAIL:{cleaned_email}")
    if cleaned_web:
        lines.append(f"URL:{cleaned_web}")
    lines.append("END:VCARD")

    payload = "\n".join(lines)
    return PayloadResult(
        qr_type="vcard",
        payload=payload,
        title=f"vCard: {full_name}",
        fields={
            "first_name": fn,
            "last_name": ln,
            "phone": cleaned_phone,
            "email": cleaned_email,
            "organization": cleaned_org,
            "website": cleaned_web,
        },
    )


def build_payload_from_fields(qr_type: str, fields: Dict[str, Any]) -> PayloadResult:
    """Dispatch payload generation based on qr_type and fields dictionary."""
    qtype = (qr_type or "").strip().lower()
    if qtype == "url":
        return build_url_payload(
            url=str(fields.get("url", "")),
            strict_validate=bool(fields.get("strict_validate", True)),
        )
    if qtype == "text":
        return build_text_payload(text=str(fields.get("text", "")))
    if qtype == "wifi":
        return build_wifi_payload(
            ssid=str(fields.get("ssid", "")),
            password=str(fields.get("password", "")),
            security=str(fields.get("security", "WPA")),
            hidden=bool(fields.get("hidden", False)),
        )
    if qtype == "email":
        return build_email_payload(
            recipient=str(fields.get("recipient", "")),
            subject=str(fields.get("subject", "")),
            message=str(fields.get("message", "")),
        )
    if qtype == "phone":
        return build_phone_payload(phone=str(fields.get("phone", "")))
    if qtype == "sms":
        return build_sms_payload(
            phone=str(fields.get("phone", "")),
            message=str(fields.get("message", "")),
        )
    if qtype == "vcard":
        return build_vcard_payload(
            first_name=str(fields.get("first_name", "")),
            last_name=str(fields.get("last_name", "")),
            phone=str(fields.get("phone", "")),
            email=str(fields.get("email", "")),
            organization=str(fields.get("organization", "")),
            website=str(fields.get("website", "")),
        )
    raise ValueError(f"Unsupported QR code type: {qr_type}")
