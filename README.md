# QUBIC — QR Code Studio

<p align="center">
  <img src="assets/icon.png" alt="QUBIC Logo" width="128" />
</p>

<p align="center">
  <strong>A modern, customizable, offline desktop QR Code Studio built with Python & PySide6.</strong><br/>
  Version <code>1.0.0</code> • Developed by <a href="https://github.com/kemorovv">Kemorovv</a>
</p>

**[Русская документация (README_RU.md)](README_RU.md)**

## Introduction

**QUBIC — QR Code Studio** is a standalone desktop application for creating, customizing, previewing, exporting, and managing standards-compliant QR codes completely offline. Designed with a dark-themed interface and clean modular architecture, QUBIC combines visual customization with strict scan reliability.

## Main Features

- **7 Supported QR Code Types**:
  - **URL / Website** — Automatic `https://` handling and optional strict URL format validation.
  - **Plain Text** — Multiline text encoding with a live character counter.
  - **Wi-Fi** — Standards-compatible `WIFI:` payloads supporting WPA/WPA2/WPA3, WEP, Open networks, and hidden SSIDs.
  - **Email** — Pre-populated `mailto:` links with recipient, subject, and message body.
  - **Phone Number** — Direct-dial `tel:` QR codes.
  - **SMS** — `SMSTO:` payloads with recipient number and optional text message.
  - **Contact Card (vCard 3.0)** — Complete contact cards with first/last name, phone, email, organization, and website.
- **Visual Customization**:
  - Custom **Foreground** and **Background** colors with validated HEX input, color picker dialog, preset/recent swatches, contrast warnings, and one-click reset.
  - **4 Module Styles**: *Classic* (square), *Rounded*, *Dots*, and *Soft* — engineered to preserve finder and timing patterns for reliable scanning.
  - **4 Error Correction Levels**: `L` (~7%), `M` (~15%, default), `Q` (~25%), and `H` (~30%).
  - **Flexible Output Sizes**: `256 × 256`, `512 × 512`, `1024 × 1024`, `2048 × 2048`, plus custom dimensions (`128`–`4096` px).
  - **Center Logo Integration**: Embed `PNG` or `JPG` logos with automatic scaling, adjustable size slider, optional white background pad, and automatic upgrade to High (`H`) error correction.
- **Export System**:
  - Export to **PNG** (with optional transparent background), **JPG**, and **SVG** (true vector output).
  - Sensible dated default filenames (e.g., `qubic_qr_2026-11-07.png`), clipboard copy, and quick **Open Folder** action.
- **Local SQLite History & Starter Templates**:
  - Search, filter by QR type, sort by newest/oldest, reload any previous QR code into the Generator, or export directly.
  - Curated collection of 7 starter templates for immediate customization.
- **Complete Localization & Themes**:
  - Full **English** and **Russian** interface translations switchable at runtime without restarting.
  - **Dark** (default), **Light**, and **System** themes.

## Screenshots

> *Placeholders for application screenshots:*
>
> - `docs/screenshots/generator_dark.png` — *Generator Workspace & Live Preview (Dark Theme)*
> - `docs/screenshots/customization_logo.png` — *Custom Colors, Module Styles & Center Logo Integration*
> - `docs/screenshots/history_templates.png` — *Local SQLite History & Starter Templates*
> - `docs/screenshots/settings_ru.png` — *Settings & Russian Localization*

## Technology Stack

- **Python 3.11+** — Core application logic and modular architecture
- **PySide6 (Qt 6)** — Desktop graphical user interface and QSS styling
- **qrcode[pil] & Pillow** — ISO/IEC 18004 QR matrix generation and custom style rendering
- **SQLite 3** — Local persistent storage for generation history
- **PyInstaller** — Standalone Windows executable packaging
- **pytest / unittest** — Automated verification suite

## Installation Instructions

### Prerequisites

- **Operating System**: Windows 10 or Windows 11 (also compatible with Linux and macOS)
- **Python**: Python 3.11 or newer
- **Git**: Optional (for cloning the repository)

### Option 1: Installation from GitHub (Using Git)

Run the following commands in Command Prompt or PowerShell:

```bash
git clone https://github.com/kemorovv/QUBIC.git
cd QUBIC
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

*(If your repository name differs, replace `QUBIC` in the `git clone` and `cd` commands accordingly.)*

### Option 2: Running Without Cloning (ZIP Download)

1. Open the repository page on GitHub (`https://github.com/kemorovv`).
2. Click **Code** → **Download ZIP** and extract the archive to a folder on your computer.
3. Open Command Prompt or PowerShell inside the extracted `QUBIC` folder.
4. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Launch the application:
   ```bash
   python main.py
   ```

## How to Run Tests

Run the automated test suite using `pytest` or `unittest`:

```bash
pytest
```

or

```bash
python -m unittest discover -s tests -v
```

## How to Build a Standalone Windows Executable

You can package **QUBIC** into a single standalone `.exe` that runs without requiring a separately installed Python interpreter.

### Using the provided PyInstaller Spec file (Recommended)

The spec file (`build/qubic.spec`) automatically bundles `assets/`, `locales/`, `src/styles/`, and `config.json`:

```bash
pyinstaller --noconfirm build/qubic.spec
```

### Using the PyInstaller CLI directly

```bash
pyinstaller --noconfirm --windowed --onefile --name QUBIC --icon assets/icon.ico --add-data "assets;assets" --add-data "locales;locales" --add-data "src/styles;src/styles" --add-data "config.json;." main.py
```

The resulting executable will be located at `dist/QUBIC.exe`.

## Project Structure

```text
QUBIC/
├── main.py
├── requirements.txt
├── README.md
├── README_RU.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
├── config.json
├── assets/
│   ├── icon.png
│   ├── icon.ico
│   └── fonts/
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── _iso_qr_matrix.py
│   │   ├── qr_generator.py
│   │   ├── qr_payloads.py
│   │   ├── qr_exporter.py
│   │   └── image_processor.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── history_repository.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── sidebar.py
│   │   ├── generator_page.py
│   │   ├── history_page.py
│   │   ├── templates_page.py
│   │   ├── settings_page.py
│   │   └── about_page.py
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── color_picker.py
│   │   ├── qr_preview.py
│   │   ├── notification.py
│   │   └── custom_button.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── localization.py
│   │   └── settings_service.py
│   └── styles/
│       ├── theme_dark.qss
│       └── theme_light.qss
├── locales/
│   ├── en.json
│   └── ru.json
├── tests/
│   ├── test_qr_generator.py
│   ├── test_qr_payloads.py
│   ├── test_exporter.py
│   └── test_localization.py
└── build/
    └── qubic.spec
```

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for full details.

## Developer Attribution

- **Developer**: Kemorovv
- **GitHub Profile**: [https://github.com/kemorovv](https://github.com/kemorovv)
