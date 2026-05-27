from pathlib import Path

import pytest

from plexmatch import refresh
from plexmatch.cache import CacheStore
from plexmatch.models import Item, User


class FakeApi:
    def __init__(self) -> None:
        self.watchlist_calls: list[str] = []

    def account_cache_key(self) -> str:
        return "account-1"

    def users(self) -> list[User]:
        return [User("self", "Owner", True), User("friend-a", "Friend A")]

    def watchlist(self, user_id: str) -> list[Item]:
        self.watchlist_calls.append(user_id)
        return [Item(f"Item {user_id}", 2020, "movie", None, None, None)]


class FakeLocalApi:
    def __init__(self, server_url: str, token: str) -> None:
        self.server_url = server_url
        self.token = token

    def library_items(self) -> list[Item]:
        return [Item("Local", 2021, "movie", None, None, None)]


def test_ttls_use_specific_env_before_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLEX_CACHE_TTL_HOURS", "1")
    monkeypatch.setenv("PLEX_LOCAL_CACHE_TTL_HOURS", "24")

    ttls = refresh.ttls_from_env()

    assert ttls.users == 3600
    assert ttls.watchlist == 3600
    assert ttls.local == 86400


def test_refresh_once_refreshes_only_expired_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_api = FakeApi()
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", fake_api.users(), -1)
    store.set_watchlist("account-1", "self", [Item("Old self", 1990, "movie", None, None, None)], -1)
    store.set_watchlist("account-1", "friend-a", [Item("Fresh", 2020, "movie", None, None, None)], 60)
    monkeypatch.setattr(refresh, "PlexApi", lambda token: fake_api)
    monkeypatch.delenv("PLEX_SERVER_URL", raising=False)
    monkeypatch.delenv("PLEX_SERVER_TOKEN", raising=False)

    stats = refresh.refresh_once("token", cache=store, ttls=refresh.CacheTtls(60, 60, 60))

    assert stats.refreshed == 2
    assert stats.skipped == 1
    assert fake_api.watchlist_calls == ["self"]
    assert store.get_watchlist("account-1", "friend-a") == [Item("Fresh", 2020, "movie", None, None, None)]


def test_refresh_all_refreshes_all_known_users(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_api = FakeApi()
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", fake_api.users(), 60)
    store.set_watchlist("account-1", "self", [Item("Fresh", 2020, "movie", None, None, None)], 60)
    monkeypatch.setattr(refresh, "PlexApi", lambda token: fake_api)
    monkeypatch.delenv("PLEX_SERVER_URL", raising=False)
    monkeypatch.delenv("PLEX_SERVER_TOKEN", raising=False)

    refresh.refresh_once("token", force=True, cache=store, ttls=refresh.CacheTtls(60, 60, 60))

    assert fake_api.watchlist_calls == ["friend-a", "self"]


def test_failed_watchlist_refresh_keeps_stale_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FailingApi(FakeApi):
        def watchlist(self, user_id: str) -> list[Item]:
            raise refresh.PlexApiError("no access")

    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", [User("self", "Owner", True)], 60)
    stale_items = [Item("Old", 1990, "movie", None, None, None)]
    store.set_watchlist("account-1", "self", stale_items, -1)
    monkeypatch.setattr(refresh, "PlexApi", lambda token: FailingApi())
    monkeypatch.delenv("PLEX_SERVER_URL", raising=False)
    monkeypatch.delenv("PLEX_SERVER_TOKEN", raising=False)

    stats = refresh.refresh_once("token", cache=store, ttls=refresh.CacheTtls(60, 60, 60))

    assert stats.failed == 1
    assert store.get_watchlist_entry("account-1", "self").payload == stale_items


def test_refresh_local_library_when_expired(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_api = FakeApi()
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", fake_api.users(), 60)
    monkeypatch.setattr(refresh, "PlexApi", lambda token: fake_api)
    monkeypatch.setattr(refresh, "LocalPlexApi", FakeLocalApi)
    monkeypatch.setenv("PLEX_SERVER_URL", "http://localhost:32400")
    monkeypatch.setenv("PLEX_SERVER_TOKEN", "server-token")

    stats = refresh.refresh_once("token", cache=store, ttls=refresh.CacheTtls(60, 60, 60))

    assert stats.refreshed >= 1
    assert store.get_local_items("http://localhost:32400") == [Item("Local", 2021, "movie", None, None, None)]


def test_refresh_once_with_auth_recovery_uses_saved_device_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_refresh_once(token: str, force=False, cache=None, ttls=None):
        calls.append(token)
        if token == "expired-token":
            raise refresh.PlexAuthError("rejected")
        return refresh.RefreshStats(checked=1, refreshed=1)

    monkeypatch.setattr(refresh, "refresh_once", fake_refresh_once)
    monkeypatch.setattr(refresh, "refresh_token_from_device_auth", lambda: "fresh-token")

    token, stats = refresh.refresh_once_with_auth_recovery("expired-token")

    assert token == "fresh-token"
    assert stats.refreshed == 1
    assert calls == ["expired-token", "fresh-token"]
    assert any("--auth-refresh" in message for message in stats.messages)


def test_refresh_once_with_auth_recovery_reports_sanitized_refresh_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_refresh_once(token: str, force=False, cache=None, ttls=None):
        raise refresh.PlexAuthError("bad token")

    def fake_refresh_token():
        raise refresh.PinAuthServiceError("refresh failed")

    monkeypatch.setattr(refresh, "refresh_once", fake_refresh_once)
    monkeypatch.setattr(refresh, "refresh_token_from_device_auth", fake_refresh_token)

    token, stats = refresh.refresh_once_with_auth_recovery("expired-token")

    assert token == "expired-token"
    assert stats.failed == 1
    joined = "\n".join(stats.messages)
    assert "refresh failed" in joined
    assert "expired-token" not in joined
