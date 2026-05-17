import argparse
import importlib
import os
import random

from plexmatch.matching import overlaps
from plexmatch.output import print_matches, print_users
from plexmatch.scoring import score_items


REQUIRED_PACKAGES = ("httpx",)
OPTIONAL_PACKAGES = ("dotenv",)


def token_from_env_or_arg(arg_token: str | None) -> str:
    if importlib.util.find_spec("dotenv"):
        dotenv = importlib.import_module("dotenv")
        dotenv.load_dotenv()
    token = (arg_token or os.getenv("PLEX_TOKEN") or "").strip()
    if not token:
        raise ValueError("Missing Plex token. Set PLEX_TOKEN in environment/.env or pass --token.")
    return token


def missing_required_packages() -> list[str]:
    return [name for name in REQUIRED_PACKAGES if importlib.util.find_spec(name) is None]


def assert_runtime_dependencies() -> None:
    missing = missing_required_packages()
    if not missing:
        return
    joined = ", ".join(missing)
    raise SystemExit(
        f"Missing required dependencies: {joined}. "
        "Run `pip install -r requirements.txt` and retry."
    )


def main() -> int:
    p = argparse.ArgumentParser(prog="plexmatch")
    p.add_argument("--token")
    p.add_argument("--list-users", action="store_true")
    p.add_argument("--user-a")
    p.add_argument("--user-b")
    p.add_argument("--random", action="store_true", dest="pick_random")
    p.add_argument("--top", type=int)
    p.add_argument("--type", choices=["all", "movie", "show", "movies", "shows"], default="all")
    p.add_argument("--format", choices=["table", "json"], default="table")
    args = p.parse_args()

    assert_runtime_dependencies()
    from plexmatch.api.graphql import PlexApi

    token = token_from_env_or_arg(args.token)
    api = PlexApi(token)

    if args.list_users:
        print_users(api.users(), args.format)
        return 0

    if not (args.user_a and args.user_b):
        p.error("Use --list-users or provide --user-a and --user-b.")

    users = api.users()
    by_name = {u.title.lower(): u for u in users}
    try:
        a, b = by_name[args.user_a.lower()], by_name[args.user_b.lower()]
    except KeyError:
        raise SystemExit("One or both users are not accessible from this token.")

    normalized_type = {"movies": "movie", "shows": "show"}.get(args.type, args.type)
    found = score_items(overlaps(api.watchlist(a.id), api.watchlist(b.id), normalized_type))
    if not found:
        raise SystemExit("No overlaps found.")
    if args.pick_random:
        found = [random.choice(found)]
    print_matches(found, args.format, args.top)
    return 0
