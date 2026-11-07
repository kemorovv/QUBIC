#!/usr/bin/env python3
"""Main entry point for QUBIC — QR Code Studio."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app import run_app


if __name__ == "__main__":
    sys.exit(run_app())
