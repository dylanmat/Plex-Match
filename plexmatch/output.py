import json
from dataclasses import asdict

from rich.console import Console
from rich.table import Table

from plexmatch.models import Match, User


def print_users(users: list[User], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps([asdict(u) for u in users], indent=2))
        return
    table = Table(title="Accessible Plex Users")
    table.add_column("Name")
    table.add_column("ID")
    for u in users:
        table.add_row(u.title, u.id)
    Console().print(table)


def print_matches(matches: list[Match], fmt: str, top: int | None = None) -> None:
    data = matches[:top] if top else matches
    if fmt == "json":
        print(json.dumps([asdict(m) for m in data], indent=2))
        return
    table = Table(title="PlexMatch Results")
    for col in ("Title", "Year", "Type", "Score"):
        table.add_column(col)
    for m in data:
        table.add_row(m.title, str(m.year or ""), m.media_type or "", str(m.score))
    Console().print(table)
