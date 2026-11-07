"""Image processing, color validation, custom QR module styles, and logo integration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image, ImageDraw

_HEX_COLOR_RE = re.compile(r"^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def validate_hex_color(value: str) -> bool:
    """Return True if value is a valid 3-digit or 6-digit HEX color string."""
    if not isinstance(value, str):
        return False
    return bool(_HEX_COLOR_RE.match(value.strip()))


def normalize_hex_color(value: str) -> str:
    """Normalize a valid HEX color string to uppercase #RRGGBB format."""
    cleaned = (value or "").strip()
    if not validate_hex_color(cleaned):
        raise ValueError(f"Invalid HEX color: {value}")
    raw = cleaned.lstrip("#").upper()
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    return f"#{raw}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert a HEX color string to an (R, G, B) tuple."""
    norm = normalize_hex_color(hex_color).lstrip("#")
    return int(norm[0:2], 16), int(norm[2:4], 16), int(norm[4:6], 16)


def hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Convert a HEX color string to an (R, G, B, A) tuple."""
    r, g, b = hex_to_rgb(hex_color)
    return r, g, b, alpha


def compute_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Compute WCAG contrast ratio between foreground and background colors."""
    def _rel_lum(rgb: Tuple[int, int, int]) -> float:
        channels = []
        for c in rgb:
            v = c / 255.0
            channels.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    lum1 = _rel_lum(hex_to_rgb(fg_hex))
    lum2 = _rel_lum(hex_to_rgb(bg_hex))
    bright = max(lum1, lum2)
    dark = min(lum1, lum2)
    return (bright + 0.05) / (dark + 0.05)


def is_finder_module(r: int, c: int, raw_size: int) -> bool:
    """Return True if (r, c) in raw matrix coordinates belongs to one of the 3 finder patterns."""
    in_top_left = 0 <= r <= 6 and 0 <= c <= 6
    in_top_right = 0 <= r <= 6 and (raw_size - 7) <= c < raw_size
    in_bottom_left = (raw_size - 7) <= r < raw_size and 0 <= c <= 6
    return in_top_left or in_top_right or in_bottom_left


def render_qr_matrix_to_image(
    matrix: List[List[bool]],
    border: int,
    size: int = 1024,
    fg_color: str = "#000000",
    bg_color: str = "#FFFFFF",
    style: str = "classic",
    transparent_bg: bool = False,
    logo_path: Optional[Union[str, Path, Image.Image]] = None,
    logo_scale: float = 0.20,
    logo_white_bg: bool = True,
) -> Image.Image:
    """Render a QR boolean matrix into a high-resolution styled PIL RGBA Image."""
    target_size = max(128, min(4096, int(size)))
    fg_rgba = hex_to_rgba(fg_color, 255)
    bg_rgba = (0, 0, 0, 0) if transparent_bg else hex_to_rgba(bg_color, 255)

    style_norm = (style or "classic").strip().lower()
    if style_norm not in ("classic", "rounded", "dots", "soft"):
        style_norm = "classic"

    total_modules = len(matrix)
    raw_size = total_modules - 2 * border

    canvas = Image.new("RGBA", (target_size, target_size), bg_rgba)
    draw = ImageDraw.Draw(canvas)

    # Use exact integer module pixel size centered in target_size to prevent fractional grid jitter
    box_size = max(2, target_size // total_modules)
    qr_span = raw_size * box_size
    offset = (target_size - qr_span) // 2

    for r_idx in range(raw_size):
        row = matrix[r_idx + border]
        for c_idx in range(raw_size):
            if not row[c_idx + border]:
                continue

            x0 = offset + c_idx * box_size
            y0 = offset + r_idx * box_size
            x1 = x0 + box_size - 1
            y1 = y0 + box_size - 1

            in_structural = is_finder_module(r_idx, c_idx, raw_size) or r_idx == 6 or c_idx == 6

            if in_structural:
                draw.rectangle([x0, y0, x1, y1], fill=fg_rgba)
            elif style_norm == "classic":
                draw.rounded_rectangle([x0, y0, x1, y1], radius=1, fill=fg_rgba)
            elif style_norm == "rounded":
                radius = max(1, int(box_size * 0.28))
                draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fg_rgba)
            elif style_norm == "dots":
                draw.ellipse([x0, y0, x1, y1], fill=fg_rgba)
            elif style_norm == "soft":
                radius = max(1, int(box_size * 0.18))
                draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fg_rgba)

    if logo_path:
        canvas = apply_center_logo(
            qr_image=canvas,
            logo_source=logo_path,
            logo_scale=logo_scale,
            white_background=logo_white_bg,
        )

    return canvas


def apply_center_logo(
    qr_image: Image.Image,
    logo_source: Union[str, Path, Image.Image],
    logo_scale: float = 0.20,
    white_background: bool = True,
) -> Image.Image:
    """Embed a resized logo in the center of the QR code with an optional white backing pad."""
    if isinstance(logo_source, Image.Image):
        logo_img = logo_source.convert("RGBA")
    else:
        path = Path(logo_source)
        if not path.exists():
            raise FileNotFoundError(f"Logo file not found: {path}")
        logo_img = Image.open(path).convert("RGBA")

    clamped_scale = max(0.10, min(0.25, float(logo_scale)))
    qr_w, qr_h = qr_image.size
    max_logo_dim = int(min(qr_w, qr_h) * clamped_scale)

    logo_w, logo_h = logo_img.size
    if logo_w <= 0 or logo_h <= 0:
        return qr_image

    scale_factor = min(max_logo_dim / float(logo_w), max_logo_dim / float(logo_h))
    new_w = max(1, int(round(logo_w * scale_factor)))
    new_h = max(1, int(round(logo_h * scale_factor)))
    resized_logo = logo_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    result = qr_image.copy()
    center_x = qr_w // 2
    center_y = qr_h // 2
    paste_x = center_x - new_w // 2
    paste_y = center_y - new_h // 2

    if white_background:
        pad = max(4, int(min(qr_w, qr_h) * 0.015))
        bg_box = [
            paste_x - pad,
            paste_y - pad,
            paste_x + new_w + pad,
            paste_y + new_h + pad,
        ]
        corner_radius = max(4, int(min(new_w, new_h) * 0.18))
        draw = ImageDraw.Draw(result)
        draw.rounded_rectangle(bg_box, radius=corner_radius, fill=(255, 255, 255, 255))

    result.alpha_composite(resized_logo, dest=(paste_x, paste_y))
    return result
