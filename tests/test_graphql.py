import httpx
import pytest

from plexmatch.api import graphql
from plexmatch.api.graphql import PlexApi


def test_users_reads_plex_tv_users_xml(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_xml: dict[str, object] = {}
    get_calls: list[str] = []
    post_calls: list[str] = []

    def fake_get(url, params, headers, timeout):
        get_calls.append(url)
        request = httpx.Request("GET", url, params=params)
        if url == graphql.PLEX_TV_ACCOUNT_ENDPOINT:
            return httpx.Response(200, json={"username": "owner", "friendlyName": "Owner"}, request=request)
        captured_xml["url"] = url
        captured_xml["params"] = params
        captured_xml["headers"] = headers
        return httpx.Response(
            200,
            text=(
                '<MediaContainer size="2">'
                '<User id="1" uuid="friend-uuid-1" title="Dylan" username="dylan" />'
                '<User id="2" title="Joy" username="joy" />'
                "</MediaContainer>"
            ),
            request=request,
        )

    def fake_post(endpoint, json, headers, timeout):
        post_calls.append(endpoint)
        request = httpx.Request("POST", endpoint, json=json)
        return httpx.Response(
            200,
            json={
                "data": {
                    "allFriendsV2": [
                        {"user": {"id": "community-friend-1", "username": "Dylan"}},
                    ]
                }
            },
            request=request,
        )

    monkeypatch.setattr(graphql.httpx, "get", fake_get)
    monkeypatch.setattr(graphql.httpx, "post", fake_post)

    users = PlexApi("plex-token").users()

    assert users[0].id == "self"
    assert users[0].title == "Owner"
    assert users[0].is_self is True
    assert users[1].id == "community-friend-1"
    assert users[1].title == "Dylan"
    assert users[1].account_id == "1"
    assert users[1].community_id == "community-friend-1"
    assert users[2].id == "2"
    assert users[2].title == "Joy"
    assert get_calls == [graphql.PLEX_TV_USERS_ENDPOINT, graphql.PLEX_TV_ACCOUNT_ENDPOINT]
    assert post_calls == [graphql.COMMUNITY_ENDPOINTS[0]]
    assert captured_xml["url"] == graphql.PLEX_TV_USERS_ENDPOINT
    assert captured_xml["params"] == {"X-Plex-Token": "plex-token"}
    assert captured_xml["headers"]["Accept"] == "application/xml"
    assert "Content-Type" not in captured_xml["headers"]


def test_users_rejects_401_with_sanitized_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, params, headers, timeout):
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(401, text="Unauthorized", request=request)

    monkeypatch.setattr(graphql.httpx, "get", fake_get)

    with pytest.raises(graphql.PlexAuthError) as exc_info:
        PlexApi("secret-token").users()

    message = str(exc_info.value)
    assert "secret-token" not in message
    assert "PLEX_TOKEN" in message


def test_watchlist_self_uses_discover_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(
            200,
            json={
                "MediaContainer": {
                    "totalSize": 1,
                    "Metadata": [{"title": "Alien", "year": 1979, "type": "movie", "Guid": [{"id": "imdb://tt0078748"}]}],
                }
            },
            request=request,
        )

    monkeypatch.setattr(graphql.httpx, "get", fake_get)

    items = PlexApi("plex-token").watchlist(graphql.SELF_USER_ID)

    assert captured["url"] == f"{graphql.DISCOVER_ENDPOINT}/library/sections/watchlist/all"
    assert "X-Plex-Token" not in captured["params"]
    assert captured["headers"]["X-Plex-Token"] == "plex-token"
    assert captured["params"]["X-Plex-Container-Size"] == graphql.WATCHLIST_PAGE_SIZE
    assert captured["params"]["includeAdvanced"] == 1
    assert captured["params"]["includeMeta"] == 1
    assert captured["params"]["includeCollections"] == 1
    assert captured["params"]["includeExternalMedia"] == 1
    assert items[0].title == "Alien"
    assert items[0].imdb_id == "tt0078748"


def test_watchlist_self_falls_back_to_metadata_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get(url, params, headers, timeout):
        calls.append(url)
        request = httpx.Request("GET", url, params=params)
        if url.startswith(graphql.DISCOVER_ENDPOINT):
            return httpx.Response(400, text="Bad Request", request=request)
        return httpx.Response(
            200,
            json={
                "MediaContainer": {
                    "totalSize": 1,
                    "Metadata": [{"title": "Aliens", "year": 1986, "type": "movie"}],
                }
            },
            request=request,
        )

    monkeypatch.setattr(graphql.httpx, "get", fake_get)

    items = PlexApi("plex-token").watchlist(graphql.SELF_USER_ID)

    assert calls == [
        f"{graphql.DISCOVER_ENDPOINT}/library/sections/watchlist/all",
        f"{graphql.METADATA_ENDPOINT}/library/sections/watchlist/all",
    ]
    assert items[0].title == "Aliens"


def test_watchlist_self_400_from_all_providers_raises_sanitized_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, params, headers, timeout):
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(400, text="Bad Request", request=request)

    monkeypatch.setattr(graphql.httpx, "get", fake_get)

    with pytest.raises(graphql.PlexApiError) as exc_info:
        PlexApi("secret-token").watchlist(graphql.SELF_USER_ID)

    message = str(exc_info.value)
    assert "secret-token" not in message
    assert "provider watchlist" in message


def test_watchlist_friend_data_null_raises_sanitized_error(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(endpoint, json, headers, timeout):
        captured["variables"] = json["variables"]
        request = httpx.Request("POST", endpoint, json=json)
        return httpx.Response(
            200,
            json={"data": None, "errors": [{"message": "User not found"}]},
            request=request,
        )

    monkeypatch.setattr(graphql.httpx, "post", fake_post)

    with pytest.raises(graphql.PlexApiError) as exc_info:
        PlexApi("secret-token").watchlist("123")

    assert captured["variables"]["uuid"] == "123"
    message = str(exc_info.value)
    assert "secret-token" not in message
    assert "User not found" in message
    assert "watchlist sharing" in message


def test_watchlist_friend_reads_year_from_rich_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(endpoint, json, headers, timeout):
        captured["query"] = json["query"]
        request = httpx.Request("POST", endpoint, json=json)
        return httpx.Response(
            200,
            json={
                "data": {
                    "user": {
                        "watchlist": {
                            "nodes": [
                                {"title": "Oppenheimer", "type": "movie", "year": 2023, "guid": "plex://movie/1"},
                                {"title": "Cargo", "type": "movie", "originallyAvailableAt": "2017-10-06"},
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            },
            request=request,
        )

    monkeypatch.setattr(graphql.httpx, "post", fake_post)

    items = PlexApi("plex-token").watchlist("community-friend-1")

    assert "originallyAvailableAt" in captured["query"]
    assert [(item.title, item.year, item.guid) for item in items] == [
        ("Oppenheimer", 2023, "plex://movie/1"),
        ("Cargo", 2017, None),
    ]
