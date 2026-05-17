from __future__ import annotations

import httpx

from plexmatch.models import Item, User

COMMUNITY_ENDPOINT = "https://community.plex.tv/api"
DISCOVER_ENDPOINT = "https://discover.provider.plex.tv"


class PlexApi:
    def __init__(self, token: str) -> None:
        self._token = token.strip()

    def _base_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Plex-Product": "PlexMatch",
            "X-Plex-Version": "0.1.10",
            "X-Plex-Client-Identifier": "plexmatch-cli",
            "User-Agent": "plexmatch/0.1.10",
        }

    def _header_variants(self) -> list[dict[str, str]]:
        base = self._base_headers()
        return [{**base, "X-Plex-Token": self._token}, {**base, "Authorization": f"Bearer {self._token}"}]

    def _post_community(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query, "variables": variables or {}}
        last_response: httpx.Response | None = None
        for headers in self._header_variants():
            r = httpx.post(COMMUNITY_ENDPOINT, json=payload, headers=headers, timeout=30)
            if r.status_code != 401:
                r.raise_for_status()
                return r.json()
            last_response = r
        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("Request failed before receiving a response.")

    def _get_discover(self, path: str, params: dict[str, int | str]) -> dict:
        r = httpx.get(
            f"{DISCOVER_ENDPOINT}{path}",
            params={"X-Plex-Token": self._token, **params},
            headers=self._base_headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def users(self) -> list[User]:
        query = """
        query GetAllFriends {
          allFriendsV2 { user { id username } }
        }
        """
        data = self._post_community(query).get("data", {})
        friends = ((data.get("allFriendsV2") or []))
        return [User(id=str((f.get("user") or {}).get("id") or ""), title=(f.get("user") or {}).get("username") or "") for f in friends if (f.get("user") or {}).get("username")]

    def watchlist(self, user_id: str) -> list[Item]:
        if any(u.id == str(user_id) for u in self.users()):
            return self._watchlist_for_friend(user_id)
        return self._watchlist_for_self()

    def _watchlist_for_self(self) -> list[Item]:
        items: list[Item] = []
        start, size = 0, 300
        while True:
            data = self._get_discover(
                "/library/sections/watchlist/all",
                {"X-Plex-Container-Start": start, "X-Plex-Container-Size": size},
            )
            media = data.get("MediaContainer") or {}
            metadata = media.get("Metadata") or []
            items.extend(self._items_from_metadata(metadata))
            total = int(media.get("totalSize") or 0)
            if total <= start + size:
                break
            start += size
        return items

    def _watchlist_for_friend(self, friend_id: str) -> list[Item]:
        query = """
        query GetWatchlistHub($uuid: ID = "", $first: PaginationInt!, $after: String) {
          user(id: $uuid) {
            watchlist(first: $first, after: $after) {
              nodes { id title type }
              pageInfo { hasNextPage endCursor }
            }
          }
        }
        """
        after = None
        items: list[Item] = []
        while True:
            data = self._post_community(query, {"uuid": str(friend_id), "first": 100, "after": after}).get("data", {})
            watchlist = (((data.get("user") or {}).get("watchlist")) or {})
            nodes = watchlist.get("nodes") or []
            items.extend([Item(title=n.get("title") or "", year=None, media_type=(n.get("type") or "").lower() or None, guid=None, imdb_id=None, tmdb_id=None) for n in nodes if n.get("title")])
            page = watchlist.get("pageInfo") or {}
            if not page.get("hasNextPage") or not page.get("endCursor"):
                break
            after = page.get("endCursor")
        return items

    def _items_from_metadata(self, metadata: list[dict]) -> list[Item]:
        out: list[Item] = []
        for i in metadata:
            guids = [g.get("id") for g in (i.get("Guid") or []) if g.get("id")]
            imdb = next((g for g in guids if str(g).startswith("imdb://")), None)
            tmdb = next((g for g in guids if str(g).startswith("tmdb://")), None)
            out.append(
                Item(
                    title=i.get("title") or "",
                    year=i.get("year"),
                    media_type=(i.get("type") or "").lower() or None,
                    guid=(i.get("guid") or guids[0] if guids else None),
                    imdb_id=imdb.replace("imdb://", "") if imdb else None,
                    tmdb_id=tmdb.replace("tmdb://", "") if tmdb else None,
                )
            )
        return [i for i in out if i.title]
