from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


class SettingsService:
    def __init__(self, database_url: str = "", sqlite_fallback_path: str = "data/app_settings.sqlite3") -> None:
        self.database_url = (database_url or "").strip()
        self.sqlite_fallback_path = str(sqlite_fallback_path)
        self.backend = "sqlite"

        if self.database_url:
            try:
                with self._connect_postgres() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                self.backend = "postgres"
            except Exception as exc:
                print(f"SettingsService: PostgreSQL unavailable, fallback to SQLite ({exc})")

        self._init_db()

    def _connect_postgres(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _connect_sqlite(self) -> sqlite3.Connection:
        path = Path(self.sqlite_fallback_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        if self.backend == "postgres":
            self._init_postgres()
        else:
            self._init_sqlite()

    def _init_postgres(self) -> None:
        with self._connect_postgres() as conn:
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

    def _init_sqlite(self) -> None:
        with self._connect_sqlite() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    title TEXT NOT NULL,
                    announcement_text TEXT NOT NULL,
                    announcement_enabled INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            cur.execute(
                """
                INSERT OR IGNORE INTO app_settings (id, title, announcement_text, announcement_enabled)
                VALUES (1, ?, ?, ?)
                """,
                (
                    "Assistant Transdev",
                    "Bienvenue sur le portail Transdev.",
                    1,
                ),
            )
            conn.commit()

    def get_public_settings(self) -> dict[str, Any]:
        if self.backend == "postgres":
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT title, announcement_text, announcement_enabled FROM app_settings WHERE id = 1"
                    )
                    row = cur.fetchone()
        else:
            with self._connect_sqlite() as conn:
                cur = conn.cursor()
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
        clean_title = title.strip() or "Assistant Transdev"
        clean_announcement = announcement_text.rstrip()

        if self.backend == "postgres":
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE app_settings
                        SET title = %s,
                            announcement_text = %s,
                            announcement_enabled = %s
                        WHERE id = 1
                        """,
                        (clean_title, clean_announcement, announcement_enabled),
                    )
                conn.commit()
        else:
            with self._connect_sqlite() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE app_settings
                    SET title = ?,
                        announcement_text = ?,
                        announcement_enabled = ?
                    WHERE id = 1
                    """,
                    (clean_title, clean_announcement, int(announcement_enabled)),
                )
                conn.commit()
