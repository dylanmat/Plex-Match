from __future__ import annotations

import httpx

from plexmatch.models import Item, User

ENDPOINT = "https://community.plex.tv/api"


class PlexApi:
    def __init__(self, token: str) -> None:
        self._token = token

    def _header_variants(self) -> list[dict[str, str]]:
        base = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Plex-Product": "PlexMatch",
            "X-Plex-Version": "0.1.5",
            "X-Plex-Client-Identifier": "plexmatch-cli",
        }
        return [
            {**base, "X-Plex-Token": self._token},
            {**base, "Authorization": f"Bearer {self._token}"},
        ]

    def _post(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query, "variables": variables or {}}
        last_response: httpx.Response | None = None
        for headers in self._header_variants():
            r = httpx.post(ENDPOINT, json=payload, headers=headers, timeout=30)
            if r.status_code != 401:
                r.raise_for_status()
                return r.json()
            last_response = r

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("Request failed before receiving a response.")

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
