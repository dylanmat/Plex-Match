from plexmatch.matching import candidates, overlaps
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


def test_candidates_include_both_and_one_sided_items() -> None:
    a = [Item("A", 2020, "movie", "g1", None, None), Item("Only A", 2021, "movie", "g2", None, None)]
    b = [Item("A", 2020, "movie", "g1", None, None), Item("Only B", 2022, "movie", "g3", None, None)]

    result = candidates(a, b)

    assert [(item.title, source) for _, item, source in result] == [
        ("A", "both"),
        ("Only A", "user_a"),
        ("Only B", "user_b"),
    ]


def test_candidates_match_title_when_one_side_missing_year() -> None:
    a = [Item("Cargo", 2017, "movie", None, None, None)]
    b = [Item("Cargo", None, "movie", None, None, None)]

    result = candidates(a, b)

    assert [(item.title, item.year, source) for _, item, source in result] == [("Cargo", 2017, "both")]


def test_candidates_do_not_match_same_title_with_different_known_years() -> None:
    a = [Item("Hamlet", 1996, "movie", None, None, None)]
    b = [Item("Hamlet", 1948, "movie", None, None, None)]

    result = candidates(a, b)

    assert [(item.title, item.year, source) for _, item, source in result] == [
        ("Hamlet", 1948, "user_b"),
        ("Hamlet", 1996, "user_a"),
    ]
