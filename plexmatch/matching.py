from plexmatch.models import Item
from plexmatch.normalize import item_key


def overlaps(items_a: list[Item], items_b: list[Item], media_type: str = "all") -> list[tuple[str, Item]]:
    idx_a = {item_key(i): i for i in items_a if media_type == "all" or i.media_type == media_type}
    idx_b = {item_key(i): i for i in items_b if media_type == "all" or i.media_type == media_type}
    keys = sorted(set(idx_a) & set(idx_b))
    return [(k, idx_a[k]) for k in keys]
