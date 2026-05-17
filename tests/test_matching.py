from plexmatch.matching import overlaps
from plexmatch.models import Item


def test_overlap_uses_normalized_keys() -> None:
    a = [Item("The Matrix", 1999, "movie", None, "tt0133093", None)]
    b = [Item("Matrix", 1999, "movie", None, "tt0133093", None)]
    result = overlaps(a, b)
    assert len(result) == 1


def test_overlap_filters_type() -> None:
    a = [Item("A", 2020, "movie", "g1", None, None), Item("B", 2020, "show", "g2", None, None)]
    b = [Item("A", 2020, "movie", "g1", None, None), Item("B", 2020, "show", "g2", None, None)]
    assert len(overlaps(a, b, "movie")) == 1
