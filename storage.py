"""Persistência local de histórico, favoritos e sessão em SQLite."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from _CONFIGURA_ import SEGUNDOS_DEDUP_HISTORICO
from site_utils import normalize_host
from utils import is_http_url


class BrowserStorage:
    """Acesso sincronizado ao banco SQLite do navegador."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            str(self.database_path),
            timeout=10,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        with self._lock, self._connection:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    visited_at REAL NOT NULL
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_url_time "
                "ON history(url, visited_at DESC)"
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS favorites (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    added_at REAL NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS browser_session (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    urls_json TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    host TEXT PRIMARY KEY,
                    texto TEXT NOT NULL,
                    atualizado_em REAL NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS site_blocking_exceptions (
                    host TEXT PRIMARY KEY,
                    created_at REAL NOT NULL
                )
                """
            )

    def record_visit(self, url: str, title: str = "", visited_at: float | None = None) -> bool:
        """Registra uma navegação HTTP(S), atualizando só o título em duplicatas recentes."""
        if not is_http_url(url):
            return False
        timestamp = time.time() if visited_at is None else float(visited_at)
        clean_title = (title or "").strip() or url
        cutoff = timestamp - SEGUNDOS_DEDUP_HISTORICO
        with self._lock, self._connection:
            recent = self._connection.execute(
                """
                SELECT id FROM history
                WHERE url = ? AND visited_at >= ?
                ORDER BY visited_at DESC, id DESC LIMIT 1
                """,
                (url, cutoff),
            ).fetchone()
            if recent:
                self._connection.execute(
                    "UPDATE history SET title = ? WHERE id = ?",
                    (clean_title, recent["id"]),
                )
                return False
            self._connection.execute(
                "INSERT INTO history(url, title, visited_at) VALUES (?, ?, ?)",
                (url, clean_title, timestamp),
            )
        return True

    def get_history(self, search: str = "", limit: int = 1000) -> list[dict[str, Any]]:
        term = f"%{search.strip()}%"
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, url, title, visited_at FROM history
                WHERE (? = '%' OR title LIKE ? OR url LIKE ?)
                ORDER BY visited_at DESC, id DESC LIMIT ?
                """,
                (term, term, term, max(1, int(limit))),
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_unique(self, limit: int = 8) -> list[dict[str, Any]]:
        """Retorna visitas recentes sem repetir uma mesma URL."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, url, title, visited_at FROM history
                ORDER BY visited_at DESC, id DESC
                """
            ).fetchall()
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            item = dict(row)
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            result.append(item)
            if len(result) >= max(1, int(limit)):
                break
        return result

    def remove_history_entry(self, entry_id: int) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM history WHERE id = ?",
                (int(entry_id),),
            )
        return cursor.rowcount > 0

    def clear_history(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM history")

    def add_favorite(self, url: str, title: str = "") -> bool:
        if not is_http_url(url):
            return False
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO favorites(url, title, added_at) VALUES (?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET title = excluded.title
                """,
                (url, (title or "").strip() or url, time.time()),
            )
        return True

    def remove_favorite(self, url: str) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM favorites WHERE url = ?",
                (url,),
            )
        return cursor.rowcount > 0

    def is_favorite(self, url: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM favorites WHERE url = ?",
                (url,),
            ).fetchone()
        return row is not None

    def get_favorites(self, search: str = "") -> list[dict[str, Any]]:
        term = f"%{search.strip()}%"
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT url, title, added_at FROM favorites
                WHERE (? = '%' OR title LIKE ? OR url LIKE ?)
                ORDER BY title COLLATE NOCASE, url
                """,
                (term, term, term),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_session(self, urls: list[str]) -> None:
        clean_urls: list[str] = []
        seen: set[str] = set()
        for url in urls:
            if is_http_url(url) and url not in seen:
                clean_urls.append(url)
                seen.add(url)
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO browser_session(id, urls_json) VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET urls_json = excluded.urls_json
                """,
                (json.dumps(clean_urls, ensure_ascii=False),),
            )

    def load_session(self) -> list[str]:
        with self._lock:
            row = self._connection.execute(
                "SELECT urls_json FROM browser_session WHERE id = 1"
            ).fetchone()
        if not row:
            return []
        try:
            value = json.loads(row["urls_json"])
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(value, list):
            return []
        return [url for url in value if isinstance(url, str) and is_http_url(url)]

    def save_note(
        self,
        host: str,
        texto: str,
        atualizado_em: float | None = None,
    ) -> bool:
        site = normalize_host(host, strip_www=True)
        if not site:
            return False
        content = str(texto or "")
        with self._lock, self._connection:
            if not content.strip():
                self._connection.execute("DELETE FROM notes WHERE host = ?", (site,))
                return True
            timestamp = time.time() if atualizado_em is None else float(atualizado_em)
            self._connection.execute(
                """
                INSERT INTO notes(host, texto, atualizado_em) VALUES (?, ?, ?)
                ON CONFLICT(host) DO UPDATE SET
                    texto = excluded.texto,
                    atualizado_em = excluded.atualizado_em
                """,
                (site, content, timestamp),
            )
        return True

    def get_note(self, host: str) -> str:
        site = normalize_host(host, strip_www=True)
        if not site:
            return ""
        with self._lock:
            row = self._connection.execute(
                "SELECT texto FROM notes WHERE host = ?",
                (site,),
            ).fetchone()
        return row["texto"] if row else ""

    def has_note(self, host: str) -> bool:
        site = normalize_host(host, strip_www=True)
        if not site:
            return False
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM notes WHERE host = ?",
                (site,),
            ).fetchone()
        return row is not None

    def search_notes(self, search: str = "") -> list[dict[str, Any]]:
        term = f"%{search.strip()}%"
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT host, texto, atualizado_em FROM notes
                WHERE (? = '%%' OR host LIKE ? OR texto LIKE ?)
                ORDER BY host COLLATE NOCASE
                """,
                (term, term, term),
            ).fetchall()
        return [dict(row) for row in rows]

    def all_notes(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT host, texto, atualizado_em FROM notes
                ORDER BY host COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_site_blocking_exceptions(self) -> set[str]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT host FROM site_blocking_exceptions"
            ).fetchall()
        return {row["host"] for row in rows}

    def set_site_blocking_enabled(self, host: str, enabled: bool) -> bool:
        site = normalize_host(host, strip_www=True)
        if not site:
            return False
        with self._lock, self._connection:
            if enabled:
                self._connection.execute(
                    "DELETE FROM site_blocking_exceptions WHERE host = ?",
                    (site,),
                )
            else:
                self._connection.execute(
                    """
                    INSERT INTO site_blocking_exceptions(host, created_at)
                    VALUES (?, ?)
                    ON CONFLICT(host) DO NOTHING
                    """,
                    (site, time.time()),
                )
        return True

    def close(self) -> None:
        with self._lock:
            self._connection.close()
