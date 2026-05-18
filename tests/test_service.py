from pathlib import Path

import pytest

from plexmatch.cache import CacheError, CacheStore
from plexmatch.models import Item, User
from plexmatch.service import CachedComparisonService


def _store_with_comparisons(path: Path) -> CacheStore:
    store = CacheStore(path)
    users = [
        User("self", "Owner", True),
        User("friend-a", "Friend A"),
        User("friend-b", "Friend B"),
    ]
    store.set_users("account-1", users, 60)
    store.set_watchlist(
        "account-1",
        "self",
        [
            Item("Alien", 1979, "movie", None, "tt0078748", None),
            Item("Aliens", 1986, "movie", None, "tt0090605", None),
            Item("Only Self", 2020, "movie", "self-only", None, None),
        ],
        60,
    )
    store.set_watchlist(
        "account-1",
        "friend-a",
        [
            Item("Alien", 1979, "movie", None, "tt0078748", None),
            Item("Aliens", 1986, "movie", None, "tt0090605", None),
        ],
        60,
    )
    store.set_watchlist(
        "account-1",
        "friend-b",
        [Item("Alien", 1979, "movie", None, "tt0078748", None)],
        60,
    )
    store.set_local_items(
        "http://localhost:32400",
        [Item("Alien", 1979, "movie", None, "tt0078748", None)],
        60,
    )
    return store


def test_cached_service_ranks_users_by_total_overlap_score(tmp_path: Path) -> None:
    service = CachedComparisonService(_store_with_comparisons(tmp_path / "cache.sqlite3"))

    ranked = service.ranked_users("movie")

    assert [entry.user.id for entry in ranked] == ["friend-a", "friend-b"]
    assert ranked[0].total_score > ranked[1].total_score


def test_cached_service_reports_missing_cache_status(tmp_path: Path) -> None:
    service = CachedComparisonService(CacheStore(tmp_path / "cache.sqlite3"))

    status = service.status()

    assert status.ready is False
    assert "python -m plexmatch --list-users" in status.commands


def test_cached_service_filters_and_randomizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = CachedComparisonService(_store_with_comparisons(tmp_path / "cache.sqlite3"))

    captured: dict[str, object] = {}

    def fake_choice(population):
        captured["population"] = population
        return population[0]

    monkeypatch.setattr("plexmatch.scoring.random.choice", fake_choice)

    picked = service.random_match("friend-a", "low", "movie", top=1)

    assert picked.title == "Alien"
    assert len(captured["population"]) == 1


def test_cached_service_raises_for_missing_watchlist(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.set_users("account-1", [User("self", "Owner", True), User("friend-a", "Friend A")], 60)
    store.set_watchlist("account-1", "self", [Item("Alien", 1979, "movie", None, None, None)], 60)
    service = CachedComparisonService(store)

    with pytest.raises(CacheError):
        service.compare("friend-a")
