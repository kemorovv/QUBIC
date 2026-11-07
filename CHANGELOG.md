# Changelog

All notable changes to **QUBIC — QR Code Studio** are documented in this file.

## [1.0.0] — 2026-11-07

### Added
- **QR Code Generator Workspace**:
  - Support for 7 QR code payload types: URL / Website, Plain Text, Wi-Fi (`WPA/WPA2`, `WEP`, Open Network, Hidden SSID), Email (`mailto:`), Phone Number (`tel:`), SMS (`SMSTO:`), and Contact Card (`vCard 3.0`).
  - Input validation with localized error messages, URL protocol auto-completion (`https://`), Wi-Fi password visibility toggle, and Plain Text character counter.
- **Visual Customization Engine**:
  - Custom foreground and background colors with HEX input validation, native color picker dialog, preset/recent color swatches, WCAG contrast ratio check, and one-click reset.
  - Four QR module styles preserving finder and timing pattern readability: **Classic**, **Rounded**, **Dots**, and **Soft**.
  - Four ISO/IEC 18004 error correction levels (`L` ~7%, `M` ~15%, `Q` ~25%, `H` ~30%) with explanatory tooltips.
  - Standard output dimensions (`256 × 256`, `512 × 512`, `1024 × 1024`, `2048 × 2048`) plus custom pixel dimensions (`128` to `4096` px).
  - Center logo integration (`PNG` and `JPG`) with automatic resizing, adjustable scale slider, optional white background pad, automatic upgrade to High (`H`) error correction, and scan reliability warning.
- **Export System**:
  - High-resolution export to **PNG** (with optional transparent background), **JPG** (with custom background color), and **SVG** (true vector geometry preserving module styles and embedded logo).
  - Default dated filenames (`qubic_qr_YYYY-MM-DD.ext`), clipboard image copy, and toast notification with quick **Open Folder** action.
- **Local History (SQLite)**:
  - Persistent offline history storing QR type, title, payload, input fields, customization settings, and creation timestamp.
  - Search by content/title, filter by QR type, sort by newest/oldest, reload into Generator, quick export, single entry deletion, and Clear All with confirmation.
- **Starter Templates**:
  - Pre-configured templates for Website Landing Page, Guest Wi-Fi Access, Executive Business Contact (vCard), Social Media Link, Customer Support Email, Direct Phone Hotline, and Quick SMS Message.
- **Settings & Complete Localization**:
  - Complete **English** (`locales/en.json`) and **Russian** (`locales/ru.json`) localization with live runtime switching.
  - Dark theme (default), Light theme, and System theme support (`theme_dark.qss`, `theme_light.qss`).
  - Persistent configuration for default export format, size, error correction, export folder, and session memory.
- **Packaging & Testing**:
  - PyInstaller configuration (`build/qubic.spec`) with `sys._MEIPASS` resource resolution.
  - Automated unit test suite (`tests/`) covering payloads, QR generation/decoding, exporting, and localization parity.
