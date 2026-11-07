"""Repository for CRUD operations, search, filtering, and sorting of QR history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database.database import DatabaseManager


@dataclass
class HistoryEntry:
    """Data model representing a saved QR code generation entry."""

    id: int
    qr_type: str
    title: str
    payload: str
    fields: Dict[str, Any]
    customization: Dict[str, Any]
    created_at: str


class HistoryRepository:
    """Provides persistent storage and querying for generated QR codes."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self._db = db_manager or DatabaseManager()

    def add_entry(
        self,
        qr_type: str,
        title: str,
        payload: str,
        fields: Dict[str, Any],
        customization: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> HistoryEntry:
        """Insert a new QR generation record into the SQLite database."""
        timestamp = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields_str = json.dumps(fields, ensure_ascii=False)
        cust_str = json.dumps(customization, ensure_ascii=False)

        with self._db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO qr_history (qr_type, title, payload, fields_json, customization_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (qr_type, title, payload, fields_str, cust_str, timestamp),
            )
            conn.commit()
            entry_id = int(cursor.lastrowid or 0)

        return HistoryEntry(
            id=entry_id,
            qr_type=qr_type,
            title=title,
            payload=payload,
            fields=fields,
            customization=customization,
            created_at=timestamp,
        )

    def get_entry(self, entry_id: int) -> Optional[HistoryEntry]:
        """Retrieve a single history entry by its ID."""
        with self._db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM qr_history WHERE id = ?",
                (entry_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def list_entries(
        self,
        search_query: str = "",
        qr_type: Optional[str] = None,
        sort_order: str = "newest",
    ) -> List[HistoryEntry]:
        """List history entries filtered by search text, QR type, and sort order."""
        clauses: List[str] = []
        params: List[Any] = []

        if qr_type and qr_type != "all":
            clauses.append("qr_type = ?")
            params.append(qr_type)

        cleaned_search = (search_query or "").strip()
        if cleaned_search:
            like_pattern = f"%{cleaned_search}%"
            clauses.append("(title LIKE ? OR payload LIKE ? OR fields_json LIKE ?)")
            params.extend([like_pattern, like_pattern, like_pattern])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order_dir = "ASC" if sort_order == "oldest" else "DESC"
        sql = f"SELECT * FROM qr_history {where_sql} ORDER BY created_at {order_dir}, id {order_dir}"

        with self._db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def delete_entry(self, entry_id: int) -> bool:
        """Delete a single history entry by ID. Returns True if a row was deleted."""
        with self._db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM qr_history WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        """Delete all entries from history. Returns number of deleted rows."""
        with self._db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM qr_history")
            conn.commit()
            return cursor.rowcount

    def count(self) -> int:
        """Return total number of saved history entries."""
        with self._db.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM qr_history").fetchone()
            return int(row["cnt"]) if row else 0

    @staticmethod
    def _row_to_entry(row: Any) -> HistoryEntry:
        try:
            fields = json.loads(row["fields_json"])
        except (TypeError, json.JSONDecodeError):
            fields = {}
        try:
            customization = json.loads(row["customization_json"])
        except (TypeError, json.JSONDecodeError):
            customization = {}
        return HistoryEntry(
            id=int(row["id"]),
            qr_type=str(row["qr_type"]),
            title=str(row["title"]),
            payload=str(row["payload"]),
            fields=fields,
            customization=customization,
            created_at=str(row["created_at"]),
        )
