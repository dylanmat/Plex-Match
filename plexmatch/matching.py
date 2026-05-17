from plexmatch.models import Item
from plexmatch.normalize import item_key, normalize_title


def _filtered_index(items: list[Item], media_type: str) -> dict[str, Item]:
    return {item_key(i): i for i in items if media_type == "all" or i.media_type == media_type}


def overlaps(items_a: list[Item], items_b: list[Item], media_type: str = "all") -> list[tuple[str, Item]]:
    return [(key, item) for key, item, source in candidates(items_a, items_b, media_type) if source == "both"]


def candidates(items_a: list[Item], items_b: list[Item], media_type: str = "all") -> list[tuple[str, Item, str]]:
    idx_a = _filtered_index(items_a, media_type)
    idx_b = _filtered_index(items_b, media_type)
    matched_a: set[str] = set()
    matched_b: set[str] = set()
    out: list[tuple[str, Item, str]] = []

    for key in sorted(set(idx_a) & set(idx_b)):
        matched_a.add(key)
        matched_b.add(key)
        out.append((key, idx_a[key], "both"))

    fallback_matches = _fallback_title_matches(
        {key: item for key, item in idx_a.items() if key not in matched_a},
        {key: item for key, item in idx_b.items() if key not in matched_b},
    )
    for key_a, key_b in fallback_matches:
        matched_a.add(key_a)
        matched_b.add(key_b)
        out.append((key_a, idx_a[key_a], "both"))

    for key in sorted((set(idx_a) | set(idx_b)) - matched_a - matched_b):
        if key in matched_a or key in matched_b:
            continue
        if key in idx_a and key in idx_b:
            out.append((key, idx_a[key], "both"))
        elif key in idx_a:
            out.append((key, idx_a[key], "user_a"))
        else:
            out.append((key, idx_b[key], "user_b"))
    return sorted(out, key=lambda pair: (pair[2] != "both", pair[1].title.lower(), pair[1].year or 0))


def support_counts(
    candidate_items: list[tuple[str, Item, str]],
    other_watchlists: list[list[Item]],
    media_type: str = "all",
) -> dict[str, int]:
    counts = {key: 0 for key, _, _ in candidate_items}
    for watchlist in other_watchlists:
        filtered = [item for item in watchlist if media_type == "all" or item.media_type == media_type]
        for key, item, _ in candidate_items:
            if any(_items_match(item, other) for other in filtered):
                counts[key] += 1
    return counts


def _fallback_title_matches(idx_a: dict[str, Item], idx_b: dict[str, Item]) -> list[tuple[str, str]]:
    titles_a = _unique_title_index(idx_a)
    titles_b = _unique_title_index(idx_b)
    matches: list[tuple[str, str]] = []
    for title in sorted(set(titles_a) & set(titles_b)):
        key_a, item_a = titles_a[title]
        key_b, item_b = titles_b[title]
        if item_a.year and item_b.year and item_a.year != item_b.year:
            continue
        matches.append((key_a, key_b))
    return matches


def _items_match(a: Item, b: Item) -> bool:
    if a.media_type and b.media_type and a.media_type != b.media_type:
        return False
    if item_key(a) == item_key(b):
        return True
    if normalize_title(a.title) != normalize_title(b.title):
        return False
    return not (a.year and b.year and a.year != b.year)


def _unique_title_index(index: dict[str, Item]) -> dict[str, tuple[str, Item]]:
    grouped: dict[str, list[tuple[str, Item]]] = {}
    for key, item in index.items():
        grouped.setdefault(normalize_title(item.title), []).append((key, item))
    return {title: values[0] for title, values in grouped.items() if len(values) == 1}
