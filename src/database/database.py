"""SQLite connection and schema management for QUBIC."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from src.config import get_app_data_dir


class DatabaseManager:
    """Manages SQLite connections and initializes the local QUBIC database schema."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is not None:
            self._db_path = Path(db_path)
        else:
            self._db_path = get_app_data_dir() / "qubic_history.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    @property
    def db_path(self) -> Path:
        """Return path to the SQLite database file."""
        return self._db_path

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a configured SQLite connection with row factory."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_schema(self) -> None:
        """Ensure the qr_history table and indexes exist."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS qr_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    qr_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    fields_json TEXT NOT NULL,
                    customization_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_qr_history_type
                ON qr_history (qr_type)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_qr_history_created
                ON qr_history (created_at DESC)
                """
            )
            conn.commit()
