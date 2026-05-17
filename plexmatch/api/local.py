from __future__ import annotations

from xml.etree import ElementTree

import httpx

from plexmatch.models import Item
from plexmatch.normalize import normalize_title


class LocalPlexApiError(RuntimeError):
    pass


class LocalPlexApi:
    def __init__(self, server_url: str, token: str) -> None:
        self._server_url = server_url.rstrip("/")
        self._token = token.strip()

    def library_items(self) -> list[Item]:
        sections = self._library_sections()
        items: list[Item] = []
        for key, _section_type in sections:
            items.extend(self._section_items(key))
        return items

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/xml",
            "X-Plex-Product": "PlexMatch",
            "X-Plex-Version": "0.1.32",
            "X-Plex-Client-Identifier": "plexmatch-cli",
            "User-Agent": "plexmatch/0.1.32",
            "X-Plex-Token": self._token,
        }

    def _get_xml(self, path: str, params: dict[str, int] | None = None) -> ElementTree.Element:
        url = f"{self._server_url}{path}"
        try:
            response = httpx.get(url, params=params or {}, headers=self._headers(), timeout=30)
            if response.status_code in {401, 403}:
                raise LocalPlexApiError("Local Plex server rejected the configured token.")
            response.raise_for_status()
            return ElementTree.fromstring(response.text)
        except LocalPlexApiError:
            raise
        except httpx.HTTPError as exc:
            raise LocalPlexApiError("Local Plex server request failed.") from exc
        except ElementTree.ParseError as exc:
            raise LocalPlexApiError("Local Plex server returned invalid XML.") from exc

    def _library_sections(self) -> list[tuple[str, str]]:
        root = self._get_xml("/library/sections")
        sections: list[tuple[str, str]] = []
        for directory in root.findall("Directory"):
            section_type = (directory.attrib.get("type") or "").lower()
            key = directory.attrib.get("key")
            if key and section_type in {"movie", "show"}:
                sections.append((key, section_type))
        return sections

    def _section_items(self, section_key: str) -> list[Item]:
        root = self._get_xml(
            f"/library/sections/{section_key}/all",
            {"includeGuids": 1},
        )
        return [_item_from_metadata(metadata) for metadata in root.findall("Metadata") if metadata.attrib.get("title")]


def availability_for_candidates(
    candidates: list[tuple[str, Item, str]],
    local_items: list[Item],
) -> dict[str, bool]:
    return {
        key: _is_available_locally(item, local_items)
        for key, item, _source in candidates
    }


def _is_available_locally(item: Item, local_items: list[Item]) -> bool:
    ids = _identity_values(item)
    if ids:
        return any(ids & _identity_values(local_item) for local_item in local_items)
    return any(_title_year_match(item, local_item) for local_item in local_items)


def _item_from_metadata(metadata: ElementTree.Element) -> Item:
    guids = [guid.attrib.get("id") for guid in metadata.findall("Guid") if guid.attrib.get("id")]
    imdb = next((guid for guid in guids if guid.startswith("imdb://")), None)
    tmdb = next((guid for guid in guids if guid.startswith("tmdb://")), None)
    return Item(
        title=metadata.attrib.get("title") or "",
        year=_int_or_none(metadata.attrib.get("year")),
        media_type=(metadata.attrib.get("type") or "").lower() or None,
        guid=metadata.attrib.get("guid") or (guids[0] if guids else None),
        imdb_id=imdb.replace("imdb://", "") if imdb else None,
        tmdb_id=tmdb.replace("tmdb://", "") if tmdb else None,
    )


def _identity_values(item: Item) -> set[str]:
    values = set()
    for prefix, value in (
        ("guid", item.guid),
        ("imdb", item.imdb_id),
        ("tmdb", item.tmdb_id),
    ):
        if value:
            values.add(f"{prefix}:{value.lower()}")
    return values


def _title_year_match(a: Item, b: Item) -> bool:
    if a.media_type and b.media_type and a.media_type != b.media_type:
        return False
    if normalize_title(a.title) != normalize_title(b.title):
        return False
    return not (a.year and b.year and a.year != b.year)


def _int_or_none(value: str | None) -> int | None:
    if value and value.isdigit():
        return int(value)
    return None
