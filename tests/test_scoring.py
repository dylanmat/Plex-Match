from plexmatch.models import Item, Match
from plexmatch.scoring import high_confidence_pool, pick_random_match, score_candidates, score_items


def test_scoring_is_deterministic() -> None:
    pairs = [
        ("title:z:2000", Item("Z", 2000, "movie", None, None, None)),
        ("title:a:1990", Item("A", 1990, "movie", None, None, None)),
    ]
    scored = score_items(pairs)
    assert [m.title for m in scored] == ["A", "Z"]
    assert all(m.score == 67 for m in scored)


def test_candidate_scoring_prioritizes_overlaps_then_recommendations() -> None:
    scored = score_candidates(
        [
            ("title:only-a:2000", Item("Only A", 2000, "movie", None, None, None), "user_a"),
            ("title:both:2001", Item("Both", 2001, "movie", None, None, None), "both"),
            ("title:only-b:2002", Item("Only B", 2002, "movie", None, None, None), "user_b"),
        ]
    )

    assert [(m.title, m.score, m.source) for m in scored] == [
        ("Both", 67, "both"),
        ("Only A", 37, "user_a"),
        ("Only B", 37, "user_b"),
    ]


def test_candidate_scoring_normalizes_support_bonus() -> None:
    scored = score_candidates(
        [
            ("title:both:2001", Item("Both", 2001, "movie", None, None, None), "both"),
            ("title:only-b:2002", Item("Only B", 2002, "movie", None, None, None), "user_b"),
        ],
        {"title:both:2001": 2, "title:only-b:2002": 1},
        support_denominator=2,
    )

    assert [(m.title, m.score, m.support_count) for m in scored] == [
        ("Both", 87, 2),
        ("Only B", 47, 1),
    ]


def test_candidate_scoring_applies_local_availability_points() -> None:
    scored = score_candidates(
        [
            ("title:both:2001", Item("Both", 2001, "movie", None, None, None), "both"),
            ("title:only-b:2002", Item("Only B", 2002, "movie", None, None, None), "user_b"),
        ],
        availability={"title:both:2001": True, "title:only-b:2002": False},
    )

    assert [(m.title, m.score, m.available_locally) for m in scored] == [
        ("Both", 77, True),
        ("Only B", 27, False),
    ]


def test_candidate_scoring_treats_unknown_local_availability_as_neutral() -> None:
    scored = score_candidates(
        [("imdb:tt0078748", Item("Alien", 1979, "movie", None, "tt0078748", None), "both")]
    )

    assert scored[0].score == 70
    assert scored[0].available_locally is None


def test_candidate_scoring_uses_identity_confidence() -> None:
    scored = score_candidates(
        [
            ("imdb:tt0078748", Item("Stable", 1979, "movie", None, "tt0078748", None), "both"),
            ("title:title-year:1979", Item("Title Year", 1979, "movie", None, None, None), "both"),
            ("title:title-only:0", Item("Title Only", None, "movie", None, None, None), "both"),
        ]
    )

    assert [(match.title, match.score) for match in scored] == [
        ("Stable", 70),
        ("Title Year", 67),
        ("Title Only", 64),
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
