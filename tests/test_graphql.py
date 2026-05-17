import httpx
import pytest

from plexmatch.api import graphql
from plexmatch.api.graphql import PlexApi


def test_users_reads_plex_tv_users_xml(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_xml: dict[str, object] = {}
    calls: list[str] = []

    def fake_get(url, params, headers, timeout):
        calls.append(url)
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

    monkeypatch.setattr(graphql.httpx, "get", fake_get)

    users = PlexApi("plex-token").users()

    assert users[0].id == "self"
    assert users[0].title == "Owner"
    assert users[0].is_self is True
    assert users[1].id == "friend-uuid-1"
    assert users[1].title == "Dylan"
    assert users[2].id == "2"
    assert users[2].title == "Joy"
    assert calls == [graphql.PLEX_TV_USERS_ENDPOINT, graphql.PLEX_TV_ACCOUNT_ENDPOINT]
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
    assert captured["params"]["X-Plex-Token"] == "plex-token"
    assert items[0].title == "Alien"
    assert items[0].imdb_id == "tt0078748"
