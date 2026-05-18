from __future__ import annotations

from dataclasses import asdict, dataclass

from plexmatch.api.local import availability_for_candidates
from plexmatch.cache import CacheError, CacheStore
from plexmatch.matching import candidates, support_counts
from plexmatch.models import Item, Match, User
from plexmatch.scoring import pick_random_match, score_candidates


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


class CachedComparisonService:
    def __init__(self, cache: CacheStore | None = None) -> None:
        self.cache = cache or CacheStore()

    def status(self) -> CacheStatus:
        try:
            namespace = self.account_namespace()
            users = self.cache.get_users(namespace)
            if not users:
                return _missing_cache("Cached users were not found.")
            self_user = self.self_user(users)
            if self.cache.get_watchlist(namespace, self_user.id) is None:
                return _missing_cache("The self watchlist is not cached.")
            return CacheStatus(True, "Cache is ready.", [])
        except CacheError as exc:
            return CacheStatus(False, str(exc), _refresh_commands())

    def account_namespace(self) -> str:
        namespaces = self.cache.user_namespaces()
        if not namespaces:
            raise CacheError("Cached users were not found.")
        return namespaces[0]

    def users(self) -> list[User]:
        users = self.cache.get_users(self.account_namespace())
        if not users:
            raise CacheError("Cached users were not found.")
        return users

    def self_user(self, users: list[User] | None = None) -> User:
        users = users or self.users()
        user = next((candidate for candidate in users if candidate.is_self or candidate.id == "self"), None)
        if user is None:
            raise CacheError("Cached users do not include self.")
        return user

    def ranked_users(self, media_type: str = "all") -> list[RankedUser]:
        users = self.users()
        self_user = self.self_user(users)
        ranked: list[RankedUser] = []
        for user in users:
            if user.id == self_user.id:
                continue
            try:
                matches = self.compare(user.id, media_type)
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
        return sorted(ranked, key=lambda item: (-item.total_score, item.user.title.lower()))

    def compare(self, user_id: str, media_type: str = "all", top: int | None = None) -> list[Match]:
        normalized_type = _normalize_media_type(media_type)
        namespace = self.account_namespace()
        users = self.users()
        self_user = self.self_user(users)
        self_items = self._watchlist(namespace, self_user.id)
        other_items = self._watchlist(namespace, user_id)
        candidate_items = candidates(self_items, other_items, normalized_type)
        other_watchlists = [
            watchlist
            for user in users
            if user.id not in {self_user.id, user_id}
            for watchlist in [self.cache.get_watchlist(namespace, user.id)]
            if watchlist is not None
        ]
        availability = self._availability(candidate_items)
        matches = score_candidates(
            candidate_items,
            support_counts(candidate_items, other_watchlists, normalized_type),
            availability,
        )
        return matches[:top] if top else matches

    def random_match(self, user_id: str, mode: str, media_type: str = "all", top: int | None = None) -> Match:
        matches = self.compare(user_id, media_type, top)
        return pick_random_match(matches, mode)

    def _watchlist(self, namespace: str, user_id: str) -> list[Item]:
        items = self.cache.get_watchlist(namespace, user_id)
        if items is None:
            raise CacheError(f"Watchlist for user {user_id} is not cached.")
        return items

    def _availability(self, candidate_items: list[tuple[str, Item, str]]) -> dict[str, bool] | None:
        try:
            namespaces = self.cache.local_library_namespaces()
            if not namespaces:
                return None
            local_items = self.cache.get_cached_local_items(namespaces[0])
            if local_items is None:
                return None
            return availability_for_candidates(candidate_items, local_items)
        except CacheError:
            return None


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
