from __future__ import annotations

from xml.etree import ElementTree

import httpx

from plexmatch.models import Item, User

COMMUNITY_ENDPOINTS = [
    "https://community.plex.tv/api",
    "https://community.plex.tv/api/v2",
]
DISCOVER_ENDPOINT = "https://discover.provider.plex.tv"
METADATA_ENDPOINT = "https://metadata.provider.plex.tv"
PLEX_TV_ACCOUNT_ENDPOINT = "https://plex.tv/api/v2/user"
PLEX_TV_USERS_ENDPOINT = "https://plex.tv/api/users/"
SELF_USER_ID = "self"
WATCHLIST_PAGE_SIZE = 10


class PlexAuthError(RuntimeError):
    pass


class PlexApiError(RuntimeError):
    pass


class PlexApi:
    def __init__(self, token: str) -> None:
        self._token = token.strip()

    def _base_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Plex-Product": "PlexMatch",
            "X-Plex-Version": "0.1.18",
            "X-Plex-Client-Identifier": "plexmatch-cli",
            "User-Agent": "plexmatch/0.1.18",
        }

    def _header_variants(self) -> list[dict[str, str]]:
        base = self._base_headers()
        return [{**base, "X-Plex-Token": self._token}, {**base, "Authorization": f"Bearer {self._token}"}]

    def _post_community(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query, "variables": variables or {}}
        last_response: httpx.Response | None = None
        for endpoint in COMMUNITY_ENDPOINTS:
            for headers in self._header_variants():
                r = httpx.post(endpoint, json=payload, headers=headers, timeout=30)
                if r.status_code != 401:
                    r.raise_for_status()
                    return r.json()
                last_response = r
        if last_response is not None:
            raise PlexAuthError(
                "Plex rejected this token for the community API. "
                "Run `python -m plexmatch --auth-pin`, then save the new token to PLEX_TOKEN or pass it with --token."
            )
        raise RuntimeError("Request failed before receiving a response.")

    def _get_plex_tv_xml(self, url: str) -> ElementTree.Element:
        headers = {
            **self._base_headers(),
            "Accept": "application/xml",
        }
        headers.pop("Content-Type", None)
        response = httpx.get(url, params={"X-Plex-Token": self._token}, headers=headers, timeout=30)
        if response.status_code == 401:
            raise PlexAuthError(
                "Plex rejected this token. "
                "Run `python -m plexmatch --auth-pin`, then save the new token to PLEX_TOKEN or pass it with --token."
            )
        response.raise_for_status()
        try:
            return ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            raise PlexApiError("Plex returned an invalid XML response.") from exc

    def _get_plex_tv_json(self, url: str) -> dict:
        headers = self._base_headers()
        response = httpx.get(url, params={"X-Plex-Token": self._token}, headers=headers, timeout=30)
        if response.status_code == 401:
            raise PlexAuthError(
                "Plex rejected this token. "
                "Run `python -m plexmatch --auth-pin`, then save the new token to PLEX_TOKEN or pass it with --token."
            )
        response.raise_for_status()
        return response.json()

    def _get_provider_json(self, base_url: str, path: str, params: dict[str, int | str]) -> dict:
        headers = {
            **self._base_headers(),
            "X-Plex-Token": self._token,
        }
        r = httpx.get(
            f"{base_url}{path}",
            params=params,
            headers=headers,
            timeout=30,
        )
        if r.status_code == 401:
            raise PlexAuthError(
                "Plex rejected this token for the Discover watchlist API. "
                "Run `python -m plexmatch --auth-pin`, then save the new token to PLEX_TOKEN or pass it with --token."
            )
        if r.status_code == 400:
            raise PlexApiError(
                "Plex rejected the provider watchlist request. "
                "The token is valid for account lookup, but this watchlist endpoint did not accept the request."
            )
        r.raise_for_status()
        return r.json()

    def _get_watchlist_page(self, start: int, size: int) -> dict:
        params = {
            "includeAdvanced": 1,
            "includeMeta": 1,
            "includeCollections": 1,
            "includeExternalMedia": 1,
            "X-Plex-Container-Start": start,
            "X-Plex-Container-Size": size,
        }
        last_error: PlexApiError | None = None
        for base_url in (DISCOVER_ENDPOINT, METADATA_ENDPOINT):
            try:
                return self._get_provider_json(base_url, "/library/sections/watchlist/all", params)
            except PlexApiError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise PlexApiError("Plex provider watchlist request failed before receiving a response.")

    def users(self) -> list[User]:
        friends = self._users_from_plex_tv()
        if not friends:
            friends = self._users_from_community()
        return [self.self_user(), *friends]

    def self_user(self) -> User:
        data = self._get_plex_tv_json(PLEX_TV_ACCOUNT_ENDPOINT)
        title = data.get("title") or data.get("friendlyName") or data.get("username") or "Self"
        return User(id=SELF_USER_ID, title=str(title), is_self=True)

    def _users_from_plex_tv(self) -> list[User]:
        root = self._get_plex_tv_xml(PLEX_TV_USERS_ENDPOINT)
        users: list[User] = []
        for element in root.findall("User"):
            user_id = element.attrib.get("uuid") or element.attrib.get("id") or ""
            account_id = element.attrib.get("id")
            title = element.attrib.get("title") or element.attrib.get("username") or ""
            if user_id and title:
                users.append(User(id=str(user_id), title=title, account_id=account_id))
        return users

    def _users_from_community(self) -> list[User]:
        query = """
        query GetAllFriends {
          allFriendsV2 { user { id username } }
        }
        """
        data = self._post_community(query).get("data", {})
        friends = ((data.get("allFriendsV2") or []))
        return [User(id=str((f.get("user") or {}).get("id") or ""), title=(f.get("user") or {}).get("username") or "") for f in friends if (f.get("user") or {}).get("username")]

    def watchlist(self, user_id: str) -> list[Item]:
        if str(user_id) == SELF_USER_ID:
            return self._watchlist_for_self()
        return self._watchlist_for_friend(user_id)

    def _watchlist_for_self(self) -> list[Item]:
        items: list[Item] = []
        start, size = 0, WATCHLIST_PAGE_SIZE
        while True:
            data = self._get_watchlist_page(start, size)
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
            response = self._post_community(query, {"uuid": str(friend_id), "first": 100, "after": after})
            data = response.get("data")
            if not isinstance(data, dict):
                message = self._graphql_error_message(response)
                raise PlexApiError(
                    f"Plex could not return this friend's watchlist. {message} "
                    "Confirm the friend appears in --list-users and has watchlist sharing enabled."
                )
            watchlist = (((data.get("user") or {}).get("watchlist")) or {})
            nodes = watchlist.get("nodes") or []
            items.extend([Item(title=n.get("title") or "", year=None, media_type=(n.get("type") or "").lower() or None, guid=None, imdb_id=None, tmdb_id=None) for n in nodes if n.get("title")])
            page = watchlist.get("pageInfo") or {}
            if not page.get("hasNextPage") or not page.get("endCursor"):
                break
            after = page.get("endCursor")
        return items

    def _graphql_error_message(self, response: dict) -> str:
        errors = response.get("errors")
        if not isinstance(errors, list):
            return "The GraphQL response did not include usable data."
        messages = [str(error.get("message")) for error in errors if isinstance(error, dict) and error.get("message")]
        if not messages:
            return "The GraphQL response did not include usable data."
        return " ".join(messages[:2])

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
