"""QR Code Exporter supporting PNG (with transparency), JPG, and vector SVG."""

from __future__ import annotations

import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from PIL import Image

from src.core.image_processor import (
    hex_to_rgb,
    is_finder_module,
    normalize_hex_color,
    render_qr_matrix_to_image,
)
from src.core.qr_generator import GeneratedQRResult


def get_default_export_filename(fmt: str = "PNG", date_override: Optional[datetime] = None) -> str:
    """Return a default filename such as 'qubic_qr_2026-11-07.png'."""
    ext = (fmt or "PNG").strip().lower()
    if ext not in ("png", "jpg", "jpeg", "svg"):
        ext = "png"
    if ext == "jpeg":
        ext = "jpg"
    dt = date_override or datetime.now()
    return f"qubic_qr_{dt.strftime('%Y-%m-%d')}.{ext}"


class QRExporter:
    """Handles exporting generated QR codes to PNG, JPG, and vector SVG files."""

    @staticmethod
    def export_png(
        qr_result: GeneratedQRResult,
        output_path: Union[str, Path],
        size: Optional[int] = None,
        transparent_bg: Optional[bool] = None,
    ) -> Path:
        """Export QR code as a high-quality PNG image (with optional transparency)."""
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        cfg = qr_result.config
        export_size = max(128, min(4096, int(size if size is not None else cfg.size)))
        use_transparent = cfg.transparent_bg if transparent_bg is None else bool(transparent_bg)

        img = render_qr_matrix_to_image(
            matrix=qr_result.matrix,
            border=qr_result.border,
            size=export_size,
            fg_color=cfg.fg_color,
            bg_color=cfg.bg_color,
            style=cfg.style,
            transparent_bg=use_transparent,
            logo_path=cfg.logo_path,
            logo_scale=cfg.logo_scale,
            logo_white_bg=cfg.logo_white_bg,
        )
        img.save(dest, format="PNG", optimize=True)
        return dest

    @staticmethod
    def export_jpg(
        qr_result: GeneratedQRResult,
        output_path: Union[str, Path],
        size: Optional[int] = None,
        bg_color: Optional[str] = None,
    ) -> Path:
        """Export QR code as a high-quality RGB JPEG image."""
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        cfg = qr_result.config
        export_size = max(128, min(4096, int(size if size is not None else cfg.size)))
        effective_bg = normalize_hex_color(bg_color if bg_color is not None else cfg.bg_color)

        rgba_img = render_qr_matrix_to_image(
            matrix=qr_result.matrix,
            border=qr_result.border,
            size=export_size,
            fg_color=cfg.fg_color,
            bg_color=effective_bg,
            style=cfg.style,
            transparent_bg=False,
            logo_path=cfg.logo_path,
            logo_scale=cfg.logo_scale,
            logo_white_bg=cfg.logo_white_bg,
        )
        rgb_canvas = Image.new("RGB", rgba_img.size, hex_to_rgb(effective_bg))
        rgb_canvas.paste(rgba_img, mask=rgba_img.split()[3])
        rgb_canvas.save(dest, format="JPEG", quality=95, subsampling=0)
        return dest

    @staticmethod
    def build_svg_string(
        qr_result: GeneratedQRResult,
        size: Optional[int] = None,
        transparent_bg: Optional[bool] = None,
    ) -> str:
        """Build a standards-compliant vector SVG string preserving QR module geometry."""
        cfg = qr_result.config
        export_size = max(128, min(4096, int(size if size is not None else cfg.size)))
        use_transparent = cfg.transparent_bg if transparent_bg is None else bool(transparent_bg)
        fg_hex = normalize_hex_color(cfg.fg_color)
        bg_hex = normalize_hex_color(cfg.bg_color)
        style_norm = cfg.style

        matrix = qr_result.matrix
        border = qr_result.border
        total_modules = len(matrix)
        raw_size = total_modules - 2 * border
        scale = 10.0
        view_size = total_modules * scale

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{export_size}" height="{export_size}" '
                f'viewBox="0 0 {view_size:.2f} {view_size:.2f}" '
                f'shape-rendering="geometricPrecision">'
            ),
        ]

        if not use_transparent:
            lines.append(
                f'  <rect width="{view_size:.2f}" height="{view_size:.2f}" fill="{bg_hex}"/>'
            )

        lines.append(f'  <g fill="{fg_hex}">')
        for r_idx, row in enumerate(matrix):
            for c_idx, is_dark in enumerate(row):
                if not is_dark:
                    continue
                x = c_idx * scale
                y = r_idx * scale
                raw_r = r_idx - border
                raw_c = c_idx - border
                in_finder = (
                    0 <= raw_r < raw_size
                    and 0 <= raw_c < raw_size
                    and is_finder_module(raw_r, raw_c, raw_size)
                )

                if style_norm == "classic":
                    lines.append(
                        f'    <rect x="{x:.2f}" y="{y:.2f}" width="{scale:.2f}" height="{scale:.2f}"/>'
                    )
                elif style_norm == "rounded":
                    if in_finder:
                        rx = scale * 0.22
                        lines.append(
                            f'    <rect x="{x:.2f}" y="{y:.2f}" width="{scale:.2f}" height="{scale:.2f}" rx="{rx:.2f}" ry="{rx:.2f}"/>'
                        )
                    else:
                        pad = scale * 0.04
                        w = scale - 2 * pad
                        rx = scale * 0.36
                        lines.append(
                            f'    <rect x="{x + pad:.2f}" y="{y + pad:.2f}" width="{w:.2f}" height="{w:.2f}" rx="{rx:.2f}" ry="{rx:.2f}"/>'
                        )
                elif style_norm == "dots":
                    if in_finder:
                        rx = scale * 0.25
                        lines.append(
                            f'    <rect x="{x:.2f}" y="{y:.2f}" width="{scale:.2f}" height="{scale:.2f}" rx="{rx:.2f}" ry="{rx:.2f}"/>'
                        )
                    else:
                        cx = x + scale * 0.5
                        cy = y + scale * 0.5
                        rad = scale * 0.44
                        lines.append(
                            f'    <circle cx="{cx:.2f}" cy="{cy:.2f}" r="{rad:.2f}"/>'
                        )
                elif style_norm == "soft":
                    rx = scale * 0.24
                    lines.append(
                        f'    <rect x="{x:.2f}" y="{y:.2f}" width="{scale:.2f}" height="{scale:.2f}" rx="{rx:.2f}" ry="{rx:.2f}"/>'
                    )
        lines.append("  </g>")

        if cfg.logo_path:
            logo_file = Path(cfg.logo_path)
            if logo_file.exists():
                with Image.open(logo_file) as l_img:
                    rgba_logo = l_img.convert("RGBA")
                    buf = io.BytesIO()
                    rgba_logo.save(buf, format="PNG")
                    b64_data = base64.b64encode(buf.getvalue()).decode("ascii")

                    clamped_scale = max(0.10, min(0.25, float(cfg.logo_scale)))
                    max_dim = view_size * clamped_scale
                    lw, lh = rgba_logo.size
                    s_factor = min(max_dim / float(lw), max_dim / float(lh))
                    draw_w = lw * s_factor
                    draw_h = lh * s_factor
                    lx = (view_size - draw_w) / 2.0
                    ly = (view_size - draw_h) / 2.0

                    if cfg.logo_white_bg:
                        pad = view_size * 0.018
                        rx = min(draw_w, draw_h) * 0.18
                        lines.append(
                            f'  <rect x="{lx - pad:.2f}" y="{ly - pad:.2f}" '
                            f'width="{draw_w + 2 * pad:.2f}" height="{draw_h + 2 * pad:.2f}" '
                            f'rx="{rx:.2f}" ry="{rx:.2f}" fill="#FFFFFF"/>'
                        )
                    lines.append(
                        f'  <image x="{lx:.2f}" y="{ly:.2f}" width="{draw_w:.2f}" height="{draw_h:.2f}" '
                        f'href="data:image/png;base64,{b64_data}"/>'
                    )

        lines.append("</svg>")
        return "\n".join(lines)

    @classmethod
    def export_svg(
        cls,
        qr_result: GeneratedQRResult,
        output_path: Union[str, Path],
        size: Optional[int] = None,
        transparent_bg: Optional[bool] = None,
    ) -> Path:
        """Export QR code as a vector SVG file."""
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        svg_content = cls.build_svg_string(
            qr_result=qr_result,
            size=size,
            transparent_bg=transparent_bg,
        )
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(svg_content)
        return dest

    @classmethod
    def export(
        cls,
        qr_result: GeneratedQRResult,
        output_path: Union[str, Path],
        fmt: str = "PNG",
        size: Optional[int] = None,
        transparent_bg: Optional[bool] = None,
        bg_color: Optional[str] = None,
    ) -> Path:
        """Dispatch export to PNG, JPG, or SVG based on fmt."""
        f_norm = (fmt or "PNG").strip().upper()
        if f_norm == "PNG":
            return cls.export_png(qr_result, output_path, size=size, transparent_bg=transparent_bg)
        if f_norm in ("JPG", "JPEG"):
            return cls.export_jpg(qr_result, output_path, size=size, bg_color=bg_color)
        if f_norm == "SVG":
            return cls.export_svg(qr_result, output_path, size=size, transparent_bg=transparent_bg)
        raise ValueError(f"Unsupported export format: {fmt}")
