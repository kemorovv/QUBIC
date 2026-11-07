"""Core QR Code Generator orchestrating matrix creation, error correction, and visual styling."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from src.config import DEFAULT_BG_COLOR, DEFAULT_FG_COLOR
from src.core._iso_qr_matrix import build_iso_qr_matrix
from src.core.image_processor import (
    compute_contrast_ratio,
    normalize_hex_color,
    render_qr_matrix_to_image,
)
from src.core.qr_payloads import PayloadResult, build_payload_from_fields

try:
    import qrcode  # type: ignore

    HAS_QRCODE_LIB = True
except ImportError:
    HAS_QRCODE_LIB = False


@dataclass
class QRCustomizationConfig:
    """Holds all customization settings for a QR code."""

    fg_color: str = DEFAULT_FG_COLOR
    bg_color: str = DEFAULT_BG_COLOR
    style: str = "classic"
    error_correction: str = "M"
    size: int = 1024
    transparent_bg: bool = False
    logo_path: Optional[str] = None
    logo_scale: float = 0.20
    logo_white_bg: bool = True

    def normalized(self) -> "QRCustomizationConfig":
        """Return a validated and normalized copy of the customization config."""
        fg = normalize_hex_color(self.fg_color or DEFAULT_FG_COLOR)
        bg = normalize_hex_color(self.bg_color or DEFAULT_BG_COLOR)
        style_clean = (self.style or "classic").strip().lower()
        if style_clean not in ("classic", "rounded", "dots", "soft"):
            style_clean = "classic"

        ecc_clean = (self.error_correction or "M").strip().upper()
        if ecc_clean not in ("L", "M", "Q", "H"):
            ecc_clean = "M"

        # Automatically enforce high error correction when a logo is active if set below Q
        logo_clean = (self.logo_path or "").strip() or None
        if logo_clean and ecc_clean in ("L", "M"):
            ecc_clean = "H"

        size_clean = max(128, min(4096, int(self.size or 1024)))
        scale_clean = max(0.10, min(0.25, float(self.logo_scale or 0.20)))

        return QRCustomizationConfig(
            fg_color=fg,
            bg_color=bg,
            style=style_clean,
            error_correction=ecc_clean,
            size=size_clean,
            transparent_bg=bool(self.transparent_bg),
            logo_path=logo_clean,
            logo_scale=scale_clean,
            logo_white_bg=bool(self.logo_white_bg),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a plain dictionary."""
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QRCustomizationConfig":
        """Deserialize configuration from a dictionary."""
        return cls(
            fg_color=str(data.get("fg_color", DEFAULT_FG_COLOR)),
            bg_color=str(data.get("bg_color", DEFAULT_BG_COLOR)),
            style=str(data.get("style", "classic")),
            error_correction=str(data.get("error_correction", "M")),
            size=int(data.get("size", 1024)),
            transparent_bg=bool(data.get("transparent_bg", False)),
            logo_path=data.get("logo_path") or None,
            logo_scale=float(data.get("logo_scale", 0.20)),
            logo_white_bg=bool(data.get("logo_white_bg", True)),
        ).normalized()


@dataclass
class GeneratedQRResult:
    """Encapsulates the generated QR code matrix, rendered image, and metadata."""

    qr_type: str
    title: str
    payload: str
    fields: Dict[str, Any]
    config: QRCustomizationConfig
    matrix: List[List[bool]]
    raw_matrix: List[List[bool]]
    border: int
    image: Image.Image
    contrast_ratio: float


class QRGenerator:
    """Main QR generation service supporting qrcode[pil] and ISO/IEC 18004 matrix building."""

    DEFAULT_BORDER: int = 4

    @classmethod
    def build_matrix(
        cls,
        payload: str,
        error_correction: str = "M",
        border: int = DEFAULT_BORDER,
    ) -> Tuple[List[List[bool]], List[List[bool]]]:
        """Build (matrix_with_border, raw_matrix_without_border) for the given payload."""
        if not payload:
            raise ValueError("QR payload cannot be empty.")

        ecc_key = (error_correction or "M").strip().upper()
        if HAS_QRCODE_LIB:
            ecc_map = {
                "L": qrcode.constants.ERROR_CORRECT_L,
                "M": qrcode.constants.ERROR_CORRECT_M,
                "Q": qrcode.constants.ERROR_CORRECT_Q,
                "H": qrcode.constants.ERROR_CORRECT_H,
            }
            qr_raw = qrcode.QRCode(
                version=None,
                error_correction=ecc_map.get(ecc_key, qrcode.constants.ERROR_CORRECT_M),
                box_size=10,
                border=0,
            )
            qr_raw.add_data(payload)
            qr_raw.make(fit=True)
            raw_matrix = [[bool(cell) for cell in row] for row in qr_raw.get_matrix()]

            raw_n = len(raw_matrix)
            padded_n = raw_n + border * 2
            padded: List[List[bool]] = [[False] * padded_n for _ in range(border)]
            for row in raw_matrix:
                padded.append([False] * border + list(row) + [False] * border)
            for _ in range(border):
                padded.append([False] * padded_n)
            return padded, raw_matrix

        return build_iso_qr_matrix(payload, error_correction=ecc_key, border=border)

    @classmethod
    def generate(
        cls,
        payload_result: PayloadResult,
        config: Optional[QRCustomizationConfig] = None,
    ) -> GeneratedQRResult:
        """Generate a complete styled QR code from a validated PayloadResult and config."""
        cfg = (config or QRCustomizationConfig()).normalized()
        matrix, raw_matrix = cls.build_matrix(
            payload=payload_result.payload,
            error_correction=cfg.error_correction,
            border=cls.DEFAULT_BORDER,
        )
        image = render_qr_matrix_to_image(
            matrix=matrix,
            border=cls.DEFAULT_BORDER,
            size=cfg.size,
            fg_color=cfg.fg_color,
            bg_color=cfg.bg_color,
            style=cfg.style,
            transparent_bg=cfg.transparent_bg,
            logo_path=cfg.logo_path,
            logo_scale=cfg.logo_scale,
            logo_white_bg=cfg.logo_white_bg,
        )
        contrast = compute_contrast_ratio(cfg.fg_color, cfg.bg_color)
        return GeneratedQRResult(
            qr_type=payload_result.qr_type,
            title=payload_result.title,
            payload=payload_result.payload,
            fields=payload_result.fields,
            config=cfg,
            matrix=matrix,
            raw_matrix=raw_matrix,
            border=cls.DEFAULT_BORDER,
            image=image,
            contrast_ratio=contrast,
        )

    @classmethod
    def generate_from_fields(
        cls,
        qr_type: str,
        fields: Dict[str, Any],
        config: Optional[QRCustomizationConfig] = None,
    ) -> GeneratedQRResult:
        """Build payload from fields and generate the styled QR code."""
        payload_res = build_payload_from_fields(qr_type, fields)
        return cls.generate(payload_res, config=config)
