from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable, TypeVar

from plexmatch.models import Item, User


SCHEMA_VERSION = 1
DEFAULT_CACHE_PATH = Path(".plexmatch") / "cache.sqlite3"

T = TypeVar("T")


class CacheError(RuntimeError):
    pass


class CacheStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else cache_path()

    def clear(self) -> None:
        try:
            if self.path.exists():
                self.path.unlink()
        except OSError as exc:
            raise CacheError("Could not clear cache.") from exc

    def get_users(self, namespace: str) -> list[User] | None:
        return self._get_json(namespace, "users", "all", _users_from_payload)

    def set_users(self, namespace: str, users: list[User], ttl_seconds: int) -> None:
        self._set_json(namespace, "users", "all", [asdict(user) for user in users], ttl_seconds)

    def get_watchlist(self, namespace: str, user_id: str) -> list[Item] | None:
        return self._get_json(namespace, "watchlist", user_id, _items_from_payload)

    def set_watchlist(self, namespace: str, user_id: str, items: list[Item], ttl_seconds: int) -> None:
        self._set_json(namespace, "watchlist", user_id, [asdict(item) for item in items], ttl_seconds)

    def get_local_items(self, server_url: str) -> list[Item] | None:
        return self._get_json(_normalize_server_url(server_url), "local_library", "all", _items_from_payload)

    def set_local_items(self, server_url: str, items: list[Item], ttl_seconds: int) -> None:
        self._set_json(_normalize_server_url(server_url), "local_library", "all", [asdict(item) for item in items], ttl_seconds)

    def user_namespaces(self) -> list[str]:
        return self._list_namespaces("users")

    def local_library_namespaces(self) -> list[str]:
        return self._list_namespaces("local_library")

    def get_cached_local_items(self, namespace: str) -> list[Item] | None:
        return self._get_json(namespace, "local_library", "all", _items_from_payload)

    def _list_namespaces(self, kind: str) -> list[str]:
        now = int(time.time())
        conn: sqlite3.Connection | None = None
        try:
            conn = self._connect()
            rows = conn.execute(
                """
                SELECT namespace
                FROM cache_entries
                WHERE kind = ? AND expires_at > ?
                ORDER BY created_at DESC
                """,
                (kind, now),
            ).fetchall()
            return [str(row["namespace"]) for row in rows]
        except (OSError, sqlite3.Error) as exc:
            raise CacheError("Could not read cache.") from exc
        finally:
            if conn is not None:
                conn.close()

    def _get_json(self, namespace: str, kind: str, key: str, factory: Callable[[object], T]) -> T | None:
        now = int(time.time())
        conn: sqlite3.Connection | None = None
        try:
            conn = self._connect()
            row = conn.execute(
                """
                SELECT payload, expires_at
                FROM cache_entries
                WHERE namespace = ? AND kind = ? AND cache_key = ?
                """,
                (namespace, kind, key),
            ).fetchone()
            if row is None:
                return None
            if int(row["expires_at"]) <= now:
                conn.execute(
                    "DELETE FROM cache_entries WHERE namespace = ? AND kind = ? AND cache_key = ?",
                    (namespace, kind, key),
                )
                conn.commit()
                return None
            return factory(json.loads(row["payload"]))
        except (OSError, sqlite3.Error, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise CacheError("Could not read cache.") from exc
        finally:
            if conn is not None:
                conn.close()

    def _set_json(self, namespace: str, kind: str, key: str, payload: object, ttl_seconds: int) -> None:
        now = int(time.time())
        conn: sqlite3.Connection | None = None
        try:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO cache_entries (namespace, kind, cache_key, payload, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, kind, cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (namespace, kind, key, json.dumps(payload), now, now + ttl_seconds),
            )
            conn.commit()
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            raise CacheError("Could not write cache.") from exc
        finally:
            if conn is not None:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                namespace TEXT NOT NULL,
                kind TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                PRIMARY KEY (namespace, kind, cache_key)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO cache_meta (key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(SCHEMA_VERSION),),
        )
        conn.commit()
        return conn


def cache_path() -> Path:
    configured = (os.getenv("PLEXMATCH_CACHE_PATH") or "").strip()
    return Path(configured) if configured else DEFAULT_CACHE_PATH


def _users_from_payload(payload: object) -> list[User]:
    if not isinstance(payload, list):
        raise ValueError("Cached users payload must be a list.")
    return [User(**item) for item in payload if isinstance(item, dict)]


def _items_from_payload(payload: object) -> list[Item]:
    if not isinstance(payload, list):
        raise ValueError("Cached items payload must be a list.")
    return [Item(**item) for item in payload if isinstance(item, dict)]


def _normalize_server_url(server_url: str) -> str:
    return server_url.strip().rstrip("/").lower()
