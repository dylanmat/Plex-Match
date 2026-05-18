from __future__ import annotations

from dataclasses import asdict, dataclass
import time

from plexmatch.api.local import availability_for_candidates
from plexmatch.cache import CacheError, CacheStore
from plexmatch.matching import candidates, support_counts
from plexmatch.models import Item, Match, User
from plexmatch.scoring import pick_random_match, score_candidates

ALL_USERS_ID = "all"


@dataclass(frozen=True)
class CacheStatus:
    ready: bool
    message: str
    commands: list[str]


@dataclass(frozen=True)
class RankedUser:
    user: User
    total_score: int
    match_count: int
    top_score: int


@dataclass
class WebSnapshot:
    cache_mtime: float
    computed_at: float
    namespace: str
    users: list[User]
    self_user: User
    watchlists: dict[str, list[Item]]
    local_items: list[Item] | None
    ranked_by_type: dict[str, list[RankedUser]]
    comparisons: dict[tuple[str, str], list[Match]]


class CachedComparisonService:
    def __init__(self, cache: CacheStore | None = None) -> None:
        self.cache = cache or CacheStore()
        self._snapshot: WebSnapshot | None = None

    def status(self) -> CacheStatus:
        try:
            self._snapshot_for_read()
            return CacheStatus(True, "Cache is ready.", [])
        except CacheError as exc:
            return CacheStatus(False, str(exc), _refresh_commands())

    def account_namespace(self) -> str:
        return self._snapshot_for_read().namespace

    def users(self) -> list[User]:
        return self._snapshot_for_read().users

    def self_user(self, users: list[User] | None = None) -> User:
        if users is None:
            return self._snapshot_for_read().self_user
        users = users or self.users()
        user = next((candidate for candidate in users if candidate.is_self or candidate.id == "self"), None)
        if user is None:
            raise CacheError("Cached users do not include self.")
        return user

    def ranked_users(self, media_type: str = "all") -> list[RankedUser]:
        normalized_type = _normalize_media_type(media_type)
        snapshot = self._snapshot_for_read()
        if normalized_type in snapshot.ranked_by_type:
            return snapshot.ranked_by_type[normalized_type]
        ranked: list[RankedUser] = []
        for user in snapshot.users:
            if user.id == snapshot.self_user.id:
                continue
            try:
                matches = self.compare(user.id, normalized_type)
            except CacheError:
                continue
            ranked.append(
                RankedUser(
                    user=user,
                    total_score=sum(match.score for match in matches),
                    match_count=len(matches),
                    top_score=max((match.score for match in matches), default=0),
                )
            )
        ranked = sorted(ranked, key=lambda item: (-item.total_score, item.user.title.lower()))
        all_matches = self.compare(ALL_USERS_ID, normalized_type)
        ranked = [
            RankedUser(
                user=User(ALL_USERS_ID, "All"),
                total_score=sum(match.score for match in all_matches),
                match_count=len(all_matches),
                top_score=max((match.score for match in all_matches), default=0),
            ),
            *ranked,
        ]
        snapshot.ranked_by_type[normalized_type] = ranked
        return ranked

    def compare(self, user_id: str, media_type: str = "all", top: int | None = None) -> list[Match]:
        normalized_type = _normalize_media_type(media_type)
        snapshot = self._snapshot_for_read()
        key = (user_id, normalized_type)
        if key not in snapshot.comparisons:
            snapshot.comparisons[key] = self._compute_comparison(snapshot, user_id, normalized_type)
        matches = snapshot.comparisons[key]
        return matches[:top] if top else matches

    def random_match(self, user_id: str, mode: str, media_type: str = "all", top: int | None = None) -> Match:
        matches = self.compare(user_id, media_type, top)
        return pick_random_match(matches, mode)

    def metadata(self) -> dict[str, float | int]:
        snapshot = self._snapshot_for_read()
        return {
            "cache_mtime": snapshot.cache_mtime,
            "computed_at": snapshot.computed_at,
        }

    def _snapshot_for_read(self) -> WebSnapshot:
        cache_mtime = self._cache_mtime()
        if self._snapshot is not None and self._snapshot.cache_mtime == cache_mtime:
            return self._snapshot
        self._snapshot = self._build_snapshot(cache_mtime)
        return self._snapshot

    def _cache_mtime(self) -> float:
        try:
            return self.cache.path.stat().st_mtime
        except OSError as exc:
            raise CacheError("Cached users were not found.") from exc

    def _build_snapshot(self, cache_mtime: float) -> WebSnapshot:
        namespaces = self.cache.user_namespaces()
        if not namespaces:
            raise CacheError("Cached users were not found.")
        namespace = namespaces[0]
        users = self.cache.get_users(namespace)
        if not users:
            raise CacheError("Cached users were not found.")
        self_user = self.self_user(users)
        watchlists: dict[str, list[Item]] = {}
        for user in users:
            items = self.cache.get_watchlist(namespace, user.id)
            if items is not None:
                watchlists[user.id] = items
        if self_user.id not in watchlists:
            raise CacheError("The self watchlist is not cached.")
        local_items = None
        local_namespaces = self.cache.local_library_namespaces()
        if local_namespaces:
            local_items = self.cache.get_cached_local_items(local_namespaces[0])
        return WebSnapshot(
            cache_mtime=cache_mtime,
            computed_at=time.time(),
            namespace=namespace,
            users=users,
            self_user=self_user,
            watchlists=watchlists,
            local_items=local_items,
            ranked_by_type={},
            comparisons={},
        )

    def _compute_comparison(self, snapshot: WebSnapshot, user_id: str, media_type: str) -> list[Match]:
        self_items = self._watchlist(snapshot, snapshot.self_user.id)
        other_items = self._all_other_items(snapshot) if user_id == ALL_USERS_ID else self._watchlist(snapshot, user_id)
        candidate_items = candidates(self_items, other_items, media_type)
        other_watchlists = [
            watchlist
            for other_user_id, watchlist in snapshot.watchlists.items()
            if other_user_id not in {snapshot.self_user.id, user_id}
        ]
        availability = self._availability(snapshot, candidate_items)
        return score_candidates(
            candidate_items,
            support_counts(candidate_items, other_watchlists, media_type),
            availability,
        )

    def _all_other_items(self, snapshot: WebSnapshot) -> list[Item]:
        return [
            item
            for user_id, watchlist in snapshot.watchlists.items()
            if user_id != snapshot.self_user.id
            for item in watchlist
        ]

    def _watchlist(self, snapshot: WebSnapshot, user_id: str) -> list[Item]:
        items = snapshot.watchlists.get(user_id)
        if items is None:
            raise CacheError(f"Watchlist for user {user_id} is not cached.")
        return items

    def _availability(self, snapshot: WebSnapshot, candidate_items: list[tuple[str, Item, str]]) -> dict[str, bool] | None:
        if snapshot.local_items is None:
            return None
        return availability_for_candidates(candidate_items, snapshot.local_items)


def ranked_user_to_dict(ranked: RankedUser) -> dict:
    return {
        "user": asdict(ranked.user),
        "total_score": ranked.total_score,
        "match_count": ranked.match_count,
        "top_score": ranked.top_score,
    }


def match_to_dict(match: Match) -> dict:
    return asdict(match)


def _missing_cache(message: str) -> CacheStatus:
    return CacheStatus(False, message, _refresh_commands())


def _refresh_commands() -> list[str]:
    return [
        "python -m plexmatch --list-users",
        'python -m plexmatch --user-a self --user-b "Friend Name"',
    ]


def _normalize_media_type(media_type: str) -> str:
    return {"movies": "movie", "shows": "show"}.get(media_type, media_type)
