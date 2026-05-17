from plexmatch.models import Item
from plexmatch.scoring import score_items


def test_scoring_is_deterministic() -> None:
    pairs = [("k1", Item("Z", 2000, "movie", None, None, None)), ("k2", Item("A", 1990, "movie", None, None, None))]
    scored = score_items(pairs)
    assert [m.title for m in scored] == ["A", "Z"]
    assert all(m.score == 100 for m in scored)
