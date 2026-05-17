from plexmatch.models import Item, Match


def score_items(pairs: list[tuple[str, Item]]) -> list[Match]:
    scored = [Match(key=k, title=i.title, year=i.year, media_type=i.media_type, score=100) for k, i in pairs]
    return sorted(scored, key=lambda m: (-m.score, m.title.lower(), m.year or 0))
