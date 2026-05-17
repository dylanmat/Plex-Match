import random

from plexmatch.models import Item, Match


SOURCE_SCORES = {
    "both": 100,
    "user_b": 10,
    "user_a": 10,
}


def score_items(pairs: list[tuple[str, Item]]) -> list[Match]:
    scored = [Match(key=k, title=i.title, year=i.year, media_type=i.media_type, score=100, source="both") for k, i in pairs]
    return _sort_matches(scored)


def score_candidates(candidates: list[tuple[str, Item, str]], support_counts: dict[str, int] | None = None) -> list[Match]:
    support_counts = support_counts or {}
    scored = [
        Match(
            key=key,
            title=item.title,
            year=item.year,
            media_type=item.media_type,
            score=SOURCE_SCORES.get(source, 0) + (support_counts.get(key, 0) * 5),
            source=source,
            support_count=support_counts.get(key, 0),
        )
        for key, item, source in candidates
    ]
    return _sort_matches(scored)


def _sort_matches(scored: list[Match]) -> list[Match]:
    return sorted(scored, key=lambda m: (-m.score, m.title.lower(), m.year or 0))


def pick_random_match(matches: list[Match], mode: str = "high") -> Match:
    if not matches:
        raise ValueError("Cannot pick from an empty match list.")
    if mode == "low":
        return random.choice(matches)
    if mode == "high":
        weights = [max(match.score, 1) for match in matches]
        return random.choices(matches, weights=weights, k=1)[0]
    raise ValueError(f"Unknown random mode: {mode}")
