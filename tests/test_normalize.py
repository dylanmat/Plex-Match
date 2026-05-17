from plexmatch.models import Item
from plexmatch.normalize import item_key


def test_item_key_prefers_guid_then_imdb_then_tmdb() -> None:
    assert item_key(Item("A", 2000, "movie", "plex://1", "tt1", "2")) == "guid:plex://1"
    assert item_key(Item("A", 2000, "movie", None, "tt1", "2")) == "imdb:tt1"
    assert item_key(Item("A", 2000, "movie", None, None, "2")) == "tmdb:2"


def test_item_key_falls_back_to_title_year() -> None:
    key = item_key(Item("The Matrix!", 1999, "movie", None, None, None))
    assert key == "title:the matrix:1999"
