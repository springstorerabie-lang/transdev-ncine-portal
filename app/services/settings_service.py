from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row


class SettingsService:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.strip()
        if not self.database_url:
            raise ValueError("DATABASE_URL est vide.")
        self._init_db()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _init_db(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_settings (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        title TEXT NOT NULL,
                        announcement_text TEXT NOT NULL,
                        announcement_enabled BOOLEAN NOT NULL DEFAULT TRUE
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO app_settings (id, title, announcement_text, announcement_enabled)
                    VALUES (1, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        "Assistant Transdev",
                        "Bienvenue sur le portail Transdev.",
                        True,
                    ),
                )
            conn.commit()

    def get_public_settings(self) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT title, announcement_text, announcement_enabled FROM app_settings WHERE id = 1"
                )
                row = cur.fetchone()

        if not row:
            raise RuntimeError("La ligne de configuration principale est introuvable.")

        return {
            "title": row["title"],
            "announcement_text": row["announcement_text"],
            "announcement_enabled": bool(row["announcement_enabled"]),
        }

    def update_settings(self, title: str, announcement_text: str, announcement_enabled: bool) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app_settings
                    SET title = %s,
                        announcement_text = %s,
                        announcement_enabled = %s
                    WHERE id = 1
                    """,
                    (title.strip(), announcement_text.strip(), announcement_enabled),
                )
            conn.commit()