import httpx
import pytest

from plexmatch.api import graphql
from plexmatch.api.graphql import PlexApi


def test_users_reads_plex_tv_users_xml(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        request = httpx.Request("GET", url, params=params)
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

    assert users[0].id == "friend-uuid-1"
    assert users[0].title == "Dylan"
    assert users[1].id == "2"
    assert users[1].title == "Joy"
    assert captured["url"] == graphql.PLEX_TV_USERS_ENDPOINT
    assert captured["params"] == {"X-Plex-Token": "plex-token"}
    assert captured["headers"]["Accept"] == "application/xml"
    assert "Content-Type" not in captured["headers"]


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
