import argparse
import sys
from pathlib import Path

import pytest

from plexmatch import cli
from plexmatch.cache import CacheStore
from plexmatch.models import Item, User


class FakeApi:
    def __init__(self) -> None:
        self.users_calls = 0
        self.watchlist_calls = 0

    def users(self):
        self.users_calls += 1
        return [User("self", "Owner", True)]

    def watchlist(self, user_id):
        self.watchlist_calls += 1
        return [Item(f"Item {user_id}", 2020, "movie", None, None, None)]


def test_cached_users_uses_fresh_cache(tmp_path: Path) -> None:
    api = FakeApi()
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", [User("self", "Cached", True)], 60)

    users = cli.cached_users(api, store, "account-1", 60)

    assert users == [User("self", "Cached", True)]
    assert api.users_calls == 0


def test_cached_watchlist_refetches_expired_cache(tmp_path: Path) -> None:
    api = FakeApi()
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_watchlist("account-1", "self", [Item("Old", 1990, "movie", None, None, None)], -1)

    items = cli.cached_watchlist(api, store, "account-1", "self", 60)

    assert items == [Item("Item self", 2020, "movie", None, None, None)]
    assert api.watchlist_calls == 1
    assert store.get_watchlist("account-1", "self") == items


def test_no_cache_bypasses_reads_and_writes(tmp_path: Path) -> None:
    api = FakeApi()
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", [User("self", "Cached", True)], 60)

    users = cli.cached_users(api, None, "account-1", 60)

    assert users == [User("self", "Owner", True)]
    assert api.users_calls == 1
    assert store.get_users("account-1") == [User("self", "Cached", True)]


def test_parse_cache_ttl_rejects_invalid_values() -> None:
    parser = argparse.ArgumentParser()

    with pytest.raises(SystemExit):
        cli.parse_cache_ttl_seconds(0, parser)


def test_clear_cache_exits_without_token_validation(monkeypatch, tmp_path: Path, capsys) -> None:
    cache_file = tmp_path / "cache.sqlite3"
    CacheStore(cache_file).set_users("account-1", [User("self", "Owner", True)], 60)
    monkeypatch.setenv("PLEXMATCH_CACHE_PATH", str(cache_file))
    monkeypatch.delenv("PLEX_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["plexmatch", "--clear-cache"])

    assert cli.main() == 0

    assert not cache_file.exists()
    assert "Cache cleared." in capsys.readouterr().out
