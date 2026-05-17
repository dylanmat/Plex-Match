import httpx
import pytest

from plexmatch.api import local
from plexmatch.api.local import LocalPlexApi, availability_for_candidates
from plexmatch.models import Item


def test_local_api_reads_sections_and_items_with_guid_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, int], dict[str, str]]] = []

    def fake_get(url, params, headers, timeout):
        calls.append((url, params, headers))
        request = httpx.Request("GET", url, params=params)
        if url.endswith("/library/sections"):
            return httpx.Response(
                200,
                text=(
                    '<MediaContainer size="3">'
                    '<Directory key="1" type="movie" />'
                    '<Directory key="2" type="show" />'
                    '<Directory key="3" type="artist" />'
                    "</MediaContainer>"
                ),
                request=request,
            )
        return httpx.Response(
            200,
            text=(
                '<MediaContainer size="1">'
                '<Video title="Alien" year="1979" type="movie" guid="plex://movie/1">'
                '<Guid id="imdb://tt0078748" />'
                '<Guid id="tmdb://348" />'
                "</Video>"
                "</MediaContainer>"
            ),
            request=request,
        )

    monkeypatch.setattr(local.httpx, "get", fake_get)

    items = LocalPlexApi("http://localhost:32400/", "server-token").library_items()

    assert [(item.title, item.imdb_id, item.tmdb_id, item.guid) for item in items] == [
        ("Alien", "tt0078748", "348", "plex://movie/1"),
        ("Alien", "tt0078748", "348", "plex://movie/1"),
    ]
    assert calls[0][0] == "http://localhost:32400/library/sections"
    assert calls[0][2]["X-Plex-Token"] == "server-token"
    assert "server-token" not in calls[0][0]
    assert calls[1][1] == {"includeGuids": 1}


def test_local_api_missing_guids_falls_back_to_title_year(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, params, headers, timeout):
        request = httpx.Request("GET", url, params=params)
        if url.endswith("/library/sections"):
            return httpx.Response(
                200,
                text='<MediaContainer><Directory key="1" type="movie" /></MediaContainer>',
                request=request,
            )
        return httpx.Response(
            200,
            text='<MediaContainer><Video title="Cargo" year="2017" type="movie" /></MediaContainer>',
            request=request,
        )

    monkeypatch.setattr(local.httpx, "get", fake_get)

    assert LocalPlexApi("http://localhost:32400", "server-token").library_items() == [
        Item("Cargo", 2017, "movie", None, None, None)
    ]


def test_availability_prefers_stable_ids_and_falls_back_to_title_year() -> None:
    candidate_items = [
        ("k1", Item("Wrong Title", 1979, "movie", None, "tt0078748", None), "both"),
        ("k2", Item("Cargo", 2017, "movie", "plex://movie/cloud-id", None, None), "both"),
        ("k3", Item("Missing", 2020, "movie", None, None, None), "user_a"),
    ]
    local_items = [
        Item("Alien", 1979, "movie", None, "tt0078748", None),
        Item("Cargo", None, "movie", None, None, None),
    ]

    assert availability_for_candidates(candidate_items, local_items) == {
        "k1": True,
        "k2": True,
        "k3": False,
    }


def test_local_api_errors_are_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, params, headers, timeout):
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(401, text="Unauthorized", request=request)

    monkeypatch.setattr(local.httpx, "get", fake_get)

    with pytest.raises(local.LocalPlexApiError) as exc_info:
        LocalPlexApi("http://localhost:32400", "secret-token").library_items()

    assert "secret-token" not in str(exc_info.value)
