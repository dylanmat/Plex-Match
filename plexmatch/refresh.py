from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from plexmatch.api.graphql import PlexApi, PlexApiError
from plexmatch.api.local import LocalPlexApi, LocalPlexApiError
from plexmatch.cache import CacheStore
from plexmatch.models import User


@dataclass(frozen=True)
class CacheTtls:
    users: int
    watchlist: int
    local: int


@dataclass
class RefreshStats:
    checked: int = 0
    refreshed: int = 0
    skipped: int = 0
    failed: int = 0
    messages: list[str] = field(default_factory=list)

    def line(self) -> str:
        return (
            f"checked={self.checked} refreshed={self.refreshed} "
            f"skipped={self.skipped} failed={self.failed}"
        )


def ttls_from_env() -> CacheTtls:
    fallback = _hours_env_value("PLEX_CACHE_TTL_HOURS", 6)
    return CacheTtls(
        users=_hours_env("PLEX_USERS_CACHE_TTL_HOURS", fallback),
        watchlist=_hours_env("PLEX_WATCHLIST_CACHE_TTL_HOURS", fallback),
        local=_hours_env("PLEX_LOCAL_CACHE_TTL_HOURS", 24),
    )


def refresh_once(
    token: str,
    force: bool = False,
    cache: CacheStore | None = None,
    ttls: CacheTtls | None = None,
) -> RefreshStats:
    store = cache or CacheStore()
    ttls = ttls or ttls_from_env()
    api = PlexApi(token)
    namespace = api.account_cache_key()
    stats = RefreshStats()

    users = _refresh_users(api, store, namespace, ttls.users, force, stats)
    if users:
        _refresh_watchlists(api, store, namespace, users, ttls.watchlist, force, stats)
    _refresh_local_library(store, ttls.local, force, stats)
    return stats


def run_scheduler(
    token: str,
    interval_minutes: float = 15,
    force: bool = False,
    cache: CacheStore | None = None,
    ttls: CacheTtls | None = None,
) -> None:
    interval_seconds = max(interval_minutes, 0.1) * 60
    while True:
        stats = refresh_once(token, force=force, cache=cache, ttls=ttls)
        print(stats.line(), flush=True)
        for message in stats.messages:
            print(message, flush=True)
        time.sleep(interval_seconds)


def _refresh_users(
    api: PlexApi,
    store: CacheStore,
    namespace: str,
    ttl_seconds: int,
    force: bool,
    stats: RefreshStats,
) -> list[User]:
    stats.checked += 1
    entry = store.get_users_entry(namespace)
    if entry and entry.is_fresh and not force:
        stats.skipped += 1
        return entry.payload
    users = api.users()
    store.set_users(namespace, users, ttl_seconds)
    stats.refreshed += 1
    return users


def _refresh_watchlists(
    api: PlexApi,
    store: CacheStore,
    namespace: str,
    users: list[User],
    ttl_seconds: int,
    force: bool,
    stats: RefreshStats,
) -> None:
    by_id = {user.id: user for user in users}
    self_user = next((user for user in users if user.is_self or user.id == "self"), None)
    user_ids = set(store.cached_watchlist_user_ids(namespace, include_stale=True))
    if self_user is not None:
        user_ids.add(self_user.id)
    if force:
        user_ids.update(by_id)
    for user_id in sorted(user_ids):
        if user_id not in by_id:
            continue
        stats.checked += 1
        entry = store.get_watchlist_entry(namespace, user_id)
        if entry and entry.is_fresh and not force:
            stats.skipped += 1
            continue
        try:
            store.set_watchlist(namespace, user_id, api.watchlist(user_id), ttl_seconds)
            stats.refreshed += 1
        except PlexApiError as exc:
            stats.failed += 1
            stats.messages.append(f"watchlist {by_id[user_id].title}: {exc}")


def _refresh_local_library(store: CacheStore, ttl_seconds: int, force: bool, stats: RefreshStats) -> None:
    server_url = (os.getenv("PLEX_SERVER_URL") or "").strip()
    server_token = (os.getenv("PLEX_SERVER_TOKEN") or "").strip()
    if not (server_url and server_token):
        return
    stats.checked += 1
    entry = store.get_local_items_entry(server_url)
    if entry and entry.is_fresh and not force:
        stats.skipped += 1
        return
    try:
        store.set_local_items(server_url, LocalPlexApi(server_url, server_token).library_items(), ttl_seconds)
        stats.refreshed += 1
    except LocalPlexApiError as exc:
        stats.failed += 1
        stats.messages.append(f"local library: {exc}")


def _hours_env(name: str, default: float) -> int:
    return int(_hours_env_value(name, default) * 3600)


def _hours_env_value(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        hours = float(default)
    else:
        hours = float(raw)
    if hours <= 0:
        raise ValueError(f"{name} must be a positive number.")
    return hours
