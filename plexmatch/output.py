import json
from dataclasses import asdict

try:
    from rich.console import Console
    from rich.table import Table
except ModuleNotFoundError:
    Console = None
    Table = None

from plexmatch.models import Match, User


def print_users(users: list[User], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps([asdict(u) for u in users], indent=2))
        return
    if Table is None or Console is None:
        print("Accessible Plex Users")
        for u in users:
            role = "self" if u.is_self else "friend"
            account = f", account={u.account_id}" if u.account_id else ""
            print(f"- {u.title} ({u.id}, {role}{account})")
        return
    table = Table(title="Accessible Plex Users")
    table.add_column("Name")
    table.add_column("ID")
    table.add_column("Role")
    table.add_column("Account ID")
    for u in users:
        table.add_row(u.title, u.id, "self" if u.is_self else "friend", u.account_id or "")
    Console().print(table)


def print_matches(matches: list[Match], fmt: str, top: int | None = None) -> None:
    data = matches[:top] if top else matches
    if fmt == "json":
        print(json.dumps([asdict(m) for m in data], indent=2))
        return
    if Table is None or Console is None:
        print("PlexMatch Results")
        for m in data:
            print(f"- {m.title} ({m.year or ''}) [{m.media_type or ''}] score={m.score}")
        return
    table = Table(title="PlexMatch Results")
    for col in ("Title", "Year", "Type", "Score"):
        table.add_column(col)
    for m in data:
        table.add_row(m.title, str(m.year or ""), m.media_type or "", str(m.score))
    Console().print(table)
