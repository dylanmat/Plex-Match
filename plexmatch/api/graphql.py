from __future__ import annotations

import httpx

from plexmatch.models import Item, User

ENDPOINT = "https://community.plex.tv/api"


class PlexApi:
    def __init__(self, token: str) -> None:
        self._headers = {"X-Plex-Token": token, "Accept": "application/json"}

    def _post(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query, "variables": variables or {}}
        r = httpx.post(ENDPOINT, json=payload, headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def users(self) -> list[User]:
        query = "query Users { users { id title username friend } }"
        data = self._post(query).get("data", {})
        raw = data.get("users") or data.get("friends") or []
        return [User(id=str(u.get("id") or u.get("uuid") or ""), title=u.get("title") or u.get("username") or "") for u in raw if (u.get("title") or u.get("username"))]

    def watchlist(self, user_id: str) -> list[Item]:
        query = "query Watchlist($userId: ID!) { watchlist(userID: $userId) { items { title year type guid imdb tmdb } } }"
        data = self._post(query, {"userId": user_id}).get("data", {})
        items = (((data.get("watchlist") or {}).get("items")) or data.get("items") or [])
        return [
            Item(
                title=i.get("title") or "",
                year=i.get("year"),
                media_type=(i.get("type") or "").lower() or None,
                guid=i.get("guid"),
                imdb_id=i.get("imdb") or i.get("imdbId"),
                tmdb_id=str(i.get("tmdb") or i.get("tmdbId") or "") or None,
            )
            for i in items
            if i.get("title")
        ]
