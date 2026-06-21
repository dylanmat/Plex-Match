import random

from plexmatch.models import Item, Match


SOURCE_SCORES = {
    "both": 50,
    "user_b": 20,
    "user_a": 20,
}
SUPPORT_POINTS = 20
LOCAL_AVAILABILITY_SCORES = {
    True: 20,
    False: 0,
    None: 10,
}


def score_items(pairs: list[tuple[str, Item]]) -> list[Match]:
    return score_candidates([(key, item, "both") for key, item in pairs])


def score_candidates(
    candidates: list[tuple[str, Item, str]],
    support_counts: dict[str, int] | None = None,
    availability: dict[str, bool] | None = None,
    support_denominator: int = 0,
) -> list[Match]:
    support_counts = support_counts or {}
    availability = availability or {}
    scored = [
        Match(
            key=key,
            title=item.title,
            year=item.year,
            media_type=item.media_type,
            score=_score_candidate(
                key,
                item,
                source,
                support_counts.get(key, 0),
                support_denominator,
                availability.get(key),
            ),
            source=source,
            support_count=support_counts.get(key, 0),
            available_locally=availability.get(key),
        )
        for key, item, source in candidates
    ]
    return _sort_matches(scored)


def _sort_matches(scored: list[Match]) -> list[Match]:
    return sorted(scored, key=lambda m: (-m.score, m.title.lower(), m.year or 0))


def _score_candidate(
    key: str,
    item: Item,
    source: str,
    support_count: int,
    support_denominator: int,
    available_locally: bool | None,
) -> int:
    score = (
        SOURCE_SCORES.get(source, 0)
        + _support_score(support_count, support_denominator)
        + LOCAL_AVAILABILITY_SCORES[available_locally]
        + _identity_confidence_score(key, item)
    )
    return min(100, score)


def _support_score(support_count: int, support_denominator: int) -> int:
    if support_denominator <= 0:
        return 0
    return min(SUPPORT_POINTS, round(SUPPORT_POINTS * support_count / support_denominator))


def _identity_confidence_score(key: str, item: Item) -> int:
    if key.startswith(("guid:", "imdb:", "tmdb:")):
        return 10
    if key.startswith("title:") and item.year:
        return 7
    return 4


def pick_random_match(matches: list[Match], mode: str = "high") -> Match:
    if not matches:
        raise ValueError("Cannot pick from an empty match list.")
    if mode == "low":
        return random.choice(matches)
    if mode == "high":
        pool = high_confidence_pool(matches)
        weights = [max(match.score, 1) for match in pool]
        return random.choices(pool, weights=weights, k=1)[0]
    raise ValueError(f"Unknown random mode: {mode}")


def high_confidence_pool(matches: list[Match]) -> list[Match]:
    if not matches:
        return []
    max_score = max(match.score for match in matches)
    return [match for match in matches if match.score > 10 and match.score >= max_score * 0.75]
