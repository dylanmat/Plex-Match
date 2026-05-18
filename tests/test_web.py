from pathlib import Path

from fastapi.testclient import TestClient

from plexmatch.cache import CacheStore
from plexmatch.models import Item, User
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


def test_missing_cache_returns_setup_guidance(tmp_path: Path) -> None:
    client = TestClient(create_app(CacheStore(tmp_path / "cache.sqlite3")))

    response = client.get("/api/users/top")

    assert response.status_code == 200
    data = response.json()
    assert data["status"]["ready"] is False
    assert "python -m plexmatch --list-users" in data["status"]["commands"]


def test_cached_users_and_comparison_endpoints(tmp_path: Path) -> None:
    client = _cached_app(tmp_path / "cache.sqlite3")

    users = client.get("/api/users/top").json()["users"]
    matches = client.get("/api/compare/friend-a?media_type=movie").json()["matches"]

    assert users[0]["user"]["id"] == "friend-a"
    assert users[0]["total_score"] > 0
    assert matches[0]["title"] == "Alien"


def test_random_endpoint_returns_valid_match(tmp_path: Path) -> None:
    client = _cached_app(tmp_path / "cache.sqlite3")

    response = client.post(
        "/api/random",
        json={"user_id": "friend-a", "mode": "high", "media_type": "movie"},
    )

    assert response.status_code == 200
    assert response.json()["match"]["title"] == "Alien"
