from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from plexmatch import web as web_module
from plexmatch.cache import CacheStore
from plexmatch.models import Item, User
from plexmatch.refresh import RefreshStats
from plexmatch.api.auth import PinAuthSession
from plexmatch.web import create_app


def _cached_app(path: Path) -> TestClient:
    store = CacheStore(path)
    store.set_users("account-1", [User("self", "Owner", True), User("friend-a", "Friend A")], 60)
    store.set_watchlist(
        "account-1",
        "self",
        [Item("Alien", 1979, "movie", None, "tt0078748", None)],
        60,
    )
    store.set_watchlist(
        "account-1",
        "friend-a",
        [Item("Alien", 1979, "movie", None, "tt0078748", None)],
        60,
    )
    return TestClient(create_app(store))


def test_dashboard_loads() -> None:
    client = TestClient(create_app(CacheStore(":memory:")))

    response = client.get("/")

    assert response.status_code == 200
    assert "PlexMatch" in response.text
    assert "spinner" in response.text
    assert ".badge.both" in response.text
    assert "sourceLabel" in response.text
    assert "mobileUserSelect" in response.text
    assert "availability yes" in response.text
    assert "<span>Local</span>" in response.text
    assert 'return "Both"' in response.text
    assert "score-pill" in response.text
    assert "supportInfo" in response.text
    assert 'id="reauthButton"' in response.text
    assert "secondary hidden" in response.text


def test_missing_cache_returns_setup_guidance(tmp_path: Path) -> None:
    client = TestClient(create_app(CacheStore(tmp_path / "cache.sqlite3")))

    response = client.get("/api/users/top")

    assert response.status_code == 200
    data = response.json()
    assert data["status"]["ready"] is False
    assert "python -m plexmatch --list-users" in data["status"]["commands"]


def test_stale_cache_still_renders_with_warning(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", [User("self", "Owner", True), User("friend-a", "Friend A")], -1)
    store.set_watchlist("account-1", "self", [Item("Alien", 1979, "movie", None, "tt0078748", None)], -1)
    store.set_watchlist("account-1", "friend-a", [Item("Alien", 1979, "movie", None, "tt0078748", None)], -1)
    client = TestClient(create_app(store))

    response = client.get("/api/users/top")

    data = response.json()
    assert data["users"]
    assert data["status"]["ready"] is True
    assert data["status"]["freshness"] == "stale"


def test_cached_users_and_comparison_endpoints(tmp_path: Path) -> None:
    client = _cached_app(tmp_path / "cache.sqlite3")

    users = client.get("/api/users/top").json()["users"]
    matches = client.get("/api/compare/friend-a?media_type=movie").json()["matches"]

    assert users[0]["user"]["id"] == "all"
    assert users[0]["total_score"] > 0
    assert matches[0]["title"] == "Alien"


def test_all_user_comparison_endpoint(tmp_path: Path) -> None:
    client = _cached_app(tmp_path / "cache.sqlite3")

    matches = client.get("/api/compare/all?media_type=movie").json()["matches"]

    assert matches[0]["title"] == "Alien"


def test_random_endpoint_returns_valid_match(tmp_path: Path) -> None:
    client = _cached_app(tmp_path / "cache.sqlite3")

    response = client.post(
        "/api/random",
        json={"user_id": "friend-a", "mode": "high", "media_type": "movie"},
    )

    assert response.status_code == 200
    assert response.json()["match"]["title"] == "Alien"


def test_user_selection_endpoint_does_not_refetch_ranked_users(tmp_path: Path, monkeypatch) -> None:
    calls = {"ranked": 0}
    real_ranked_users = web_module.CachedComparisonService.ranked_users

    def counting_ranked_users(self, media_type="all"):
        calls["ranked"] += 1
        return real_ranked_users(self, media_type)

    monkeypatch.setattr(web_module.CachedComparisonService, "ranked_users", counting_ranked_users)
    client = _cached_app(tmp_path / "cache.sqlite3")

    client.get("/api/users/top")
    client.get("/api/compare/friend-a?media_type=movie")

    assert calls["ranked"] == 1


def test_media_type_change_refetches_ranked_users(tmp_path: Path, monkeypatch) -> None:
    calls = {"ranked": 0}
    real_ranked_users = web_module.CachedComparisonService.ranked_users

    def counting_ranked_users(self, media_type="all"):
        calls["ranked"] += 1
        return real_ranked_users(self, media_type)

    monkeypatch.setattr(web_module.CachedComparisonService, "ranked_users", counting_ranked_users)
    client = _cached_app(tmp_path / "cache.sqlite3")

    client.get("/api/users/top?media_type=movie")
    client.get("/api/users/top?media_type=show")

    assert calls["ranked"] == 2


def test_random_endpoint_reuses_cached_comparison_data(tmp_path: Path, monkeypatch) -> None:
    calls = {"compare": 0}
    real_compare = web_module.CachedComparisonService.compare

    def counting_compare(self, user_id, media_type="all", top=None):
        calls["compare"] += 1
        return real_compare(self, user_id, media_type, top)

    monkeypatch.setattr(web_module.CachedComparisonService, "compare", counting_compare)
    client = _cached_app(tmp_path / "cache.sqlite3")

    client.get("/api/compare/friend-a?media_type=movie")
    client.post("/api/random", json={"user_id": "friend-a", "mode": "high", "media_type": "movie"})

    assert calls["compare"] == 2


def test_web_auth_start_returns_links_without_token(tmp_path: Path, monkeypatch) -> None:
    session = PinAuthSession(
        pin_id=1,
        code="pending-code",
        client_identifier="plexmatch-cli-generated",
        private_key_b64="",
        key_id="key-1",
        session_format_version=1,
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(web_module, "plex_token_status", lambda: {"state": "expired", "message": "expired"})
    monkeypatch.setattr(web_module, "load_pin_auth_session", lambda: None)
    monkeypatch.setattr(web_module, "start_pin_auth", lambda: session)
    client = TestClient(create_app(CacheStore(":memory:")))

    data = client.post("/api/auth/start").json()

    assert data["state"] == "pending"
    assert data["auth_url"].startswith("https://app.plex.tv/auth#?")
    assert "fallback_auth_url" in data
    assert "token" not in str(data).lower()


def test_web_auth_start_rejects_when_token_is_not_expired(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(web_module, "plex_token_status", lambda: {"state": "valid", "message": "valid"})
    client = TestClient(create_app(CacheStore(":memory:")))

    response = client.post("/api/auth/start")

    assert response.status_code == 409
    assert "expired" in response.json()["detail"]


def test_web_auth_availability_reports_only_expired_tokens_available(monkeypatch) -> None:
    monkeypatch.setattr(web_module, "plex_token_status", lambda: {"state": "expired", "message": "expired"})
    client = TestClient(create_app(CacheStore(":memory:")))

    data = client.get("/api/auth/availability").json()

    assert data == {
        "reauthorization_available": True,
        "token_status": {"state": "expired", "message": "expired"},
    }


def test_web_auth_status_updates_env_and_refreshes_cache(tmp_path: Path, monkeypatch) -> None:
    session = PinAuthSession(
        pin_id=1,
        code="pending-code",
        client_identifier="plexmatch-cli-generated",
        private_key_b64="",
        key_id="key-1",
        session_format_version=1,
    )
    calls: dict[str, str] = {}

    def fake_refresh(token: str, cache=None):
        calls["token"] = token
        return token, RefreshStats(checked=2, refreshed=1, skipped=1)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(web_module, "load_pin_auth_session", lambda: session)
    monkeypatch.setattr(web_module, "exchange_pin_for_token", lambda pin_session: "fresh-token")
    monkeypatch.setattr(web_module, "refresh_once_with_auth_recovery", fake_refresh)
    client = TestClient(create_app(CacheStore(":memory:")))

    data = client.get("/api/auth/status").json()

    assert data["state"] == "complete"
    assert data["cache"] == {"checked": 2, "refreshed": 1, "skipped": 1, "failed": 0, "messages": []}
    assert calls["token"] == "fresh-token"
    assert (tmp_path / ".env").read_text() == "PLEX_TOKEN=fresh-token\n"
    assert "fresh-token" not in str(data)


def test_web_auth_local_guard_rejects_non_loopback_client() -> None:
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.10"))

    with pytest.raises(HTTPException) as exc_info:
        web_module._require_local_request(request)

    assert exc_info.value.status_code == 403
