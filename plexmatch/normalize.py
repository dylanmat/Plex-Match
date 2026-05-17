import re

from plexmatch.models import Item


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", title.lower())).strip()


def item_key(item: Item) -> str:
    for prefix, value in (("guid", item.guid), ("imdb", item.imdb_id), ("tmdb", item.tmdb_id)):
        if value:
            return f"{prefix}:{value.lower()}"
    return f"title:{normalize_title(item.title)}:{item.year or 0}"
