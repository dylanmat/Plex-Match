from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    title: str
    is_self: bool = False


@dataclass(frozen=True)
class Item:
    title: str
    year: int | None
    media_type: str | None
    guid: str | None
    imdb_id: str | None
    tmdb_id: str | None


@dataclass(frozen=True)
class Match:
    key: str
    title: str
    year: int | None
    media_type: str | None
    score: int
