from plexmatch.models import Item, Match
from plexmatch.scoring import high_confidence_pool, pick_random_match, score_candidates, score_items


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


def test_candidate_scoring_adds_support_bonus() -> None:
    scored = score_candidates(
        [
            ("k1", Item("Both", 2001, "movie", None, None, None), "both"),
            ("k2", Item("Only B", 2002, "movie", None, None, None), "user_b"),
        ],
        {"k1": 2, "k2": 1},
    )

    assert [(m.title, m.score, m.support_count) for m in scored] == [
        ("Both", 110, 2),
        ("Only B", 30, 1),
    ]


def test_high_confidence_random_uses_score_weights(monkeypatch) -> None:
    matches = [
        Match("k1", "Low", 2000, "movie", 10),
        Match("k2", "Medium", 2001, "movie", 70),
        Match("k3", "High", 2002, "movie", 100),
    ]
    captured: dict[str, object] = {}

    def fake_choices(population, weights, k):
        captured["population"] = population
        captured["weights"] = weights
        captured["k"] = k
        return [population[0]]

    monkeypatch.setattr("plexmatch.scoring.random.choices", fake_choices)

    picked = pick_random_match(matches, "high")

    assert picked.title == "High"
    assert [match.title for match in captured["population"]] == ["High"]
    assert captured["weights"] == [100]
    assert captured["k"] == 1


def test_low_confidence_random_ignores_score(monkeypatch) -> None:
    matches = [
        Match("k1", "Low", 2000, "movie", 10),
        Match("k2", "High", 2001, "movie", 100),
    ]
    captured: dict[str, object] = {}

    def fake_choice(population):
        captured["population"] = population
        return population[0]

    monkeypatch.setattr("plexmatch.scoring.random.choice", fake_choice)

    picked = pick_random_match(matches, "low")

    assert picked.title == "Low"
    assert captured["population"] == matches


def test_high_confidence_pool_excludes_lowest_score_recommendations() -> None:
    matches = [
        Match("k1", "User A Only", 2000, "movie", 10),
        Match("k2", "User B Only", 2001, "movie", 25),
        Match("k3", "Overlap", 2002, "movie", 100),
        Match("k4", "Supported Overlap", 2003, "movie", 110),
    ]

    pool = high_confidence_pool(matches)

    assert [match.title for match in pool] == ["Overlap", "Supported Overlap"]
