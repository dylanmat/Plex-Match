import sqlite3
import time
from pathlib import Path

from plexmatch.cache import DEFAULT_CACHE_PATH, CacheStore, cache_path
from plexmatch.models import Item, User


def test_cache_path_defaults_to_project_local(monkeypatch) -> None:
    monkeypatch.delenv("PLEXMATCH_CACHE_PATH", raising=False)

    assert cache_path() == DEFAULT_CACHE_PATH


def test_cache_path_env_override(monkeypatch, tmp_path: Path) -> None:
    configured = tmp_path / "cache.sqlite3"
    monkeypatch.setenv("PLEXMATCH_CACHE_PATH", str(configured))

    assert cache_path() == configured


def test_cache_round_trips_users_watchlists_and_local_items(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache.sqlite3")
    users = [User("self", "Owner", True), User("friend-1", "Friend")]
    watchlist = [Item("Alien", 1979, "movie", None, "tt0078748", None)]
    local_items = [Item("Aliens", 1986, "movie", "plex://movie/2", None, "679")]

    store.set_users("account-1", users, 60)
    store.set_watchlist("account-1", "self", watchlist, 60)
    store.set_local_items("http://LOCALHOST:32400/", local_items, 60)

    assert store.get_users("account-1") == users
    assert store.get_watchlist("account-1", "self") == watchlist
    assert store.get_local_items("http://localhost:32400") == local_items


def test_cache_ignores_expired_entries(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", [User("self", "Owner", True)], 1)

    with sqlite3.connect(store.path) as conn:
        conn.execute("UPDATE cache_entries SET expires_at = ?", (int(time.time()) - 1,))

    assert store.get_users("account-1") is None


def test_clear_cache_removes_database_file(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", [User("self", "Owner", True)], 60)

    store.clear()

    assert not store.path.exists()


def test_cache_payload_does_not_require_or_store_tokens(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_watchlist("account-1", "self", [Item("Alien", 1979, "movie", None, None, None)], 60)

    raw = store.path.read_text(errors="ignore")

    assert "token" not in raw.lower()
