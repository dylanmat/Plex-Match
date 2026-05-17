from plexmatch.models import Item
from plexmatch.scoring import score_candidates, score_items


def test_scoring_is_deterministic() -> None:
    pairs = [("k1", Item("Z", 2000, "movie", None, None, None)), ("k2", Item("A", 1990, "movie", None, None, None))]
    scored = score_items(pairs)
    assert [m.title for m in scored] == ["A", "Z"]
    assert all(m.score == 100 for m in scored)


def test_candidate_scoring_prioritizes_overlaps_then_recommendations() -> None:
    scored = score_candidates(
        [
            ("k1", Item("Only A", 2000, "movie", None, None, None), "user_a"),
            ("k2", Item("Both", 2001, "movie", None, None, None), "both"),
            ("k3", Item("Only B", 2002, "movie", None, None, None), "user_b"),
        ]
    )

    assert [(m.title, m.score, m.source) for m in scored] == [
        ("Both", 100, "both"),
        ("Only B", 25, "user_b"),
        ("Only A", 10, "user_a"),
    ]
