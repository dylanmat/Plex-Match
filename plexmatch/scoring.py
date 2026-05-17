from plexmatch.models import Item, Match


SOURCE_SCORES = {
    "both": 100,
    "user_b": 25,
    "user_a": 10,
}


def score_items(pairs: list[tuple[str, Item]]) -> list[Match]:
    scored = [Match(key=k, title=i.title, year=i.year, media_type=i.media_type, score=100, source="both") for k, i in pairs]
    return _sort_matches(scored)


def score_candidates(candidates: list[tuple[str, Item, str]]) -> list[Match]:
    scored = [
        Match(
            key=key,
            title=item.title,
            year=item.year,
            media_type=item.media_type,
            score=SOURCE_SCORES.get(source, 0),
            source=source,
        )
        for key, item, source in candidates
    ]
    return _sort_matches(scored)


def _sort_matches(scored: list[Match]) -> list[Match]:
    return sorted(scored, key=lambda m: (-m.score, m.title.lower(), m.year or 0))
