import argparse
import importlib
import os
import random
import time

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
    p.add_argument("--auth-pin", action="store_true", help="Start/poll Plex PIN+JWK auth flow and print JWT.")
    p.add_argument("--client-id", default="plexmatch-cli", help="Plex client identifier for PIN+JWK auth.")
    p.add_argument("--auth-wait", type=int, default=0, help="Seconds to poll for PIN approval before exiting.")
    args = p.parse_args()

    assert_runtime_dependencies()
    from plexmatch.api.graphql import PlexApi

    if args.auth_pin:
        from plexmatch.api.auth import exchange_pin_for_token, load_pin_auth_session, start_pin_auth

        session = load_pin_auth_session()
        if session is None:
            session = start_pin_auth(args.client_id)
            print("Open this URL in a browser and sign in:")
            print(session.auth_url)
            if session.manual_link_code:
                print("If needed, open https://plex.tv/link and enter this 4-digit code:")
                print(session.manual_link_code)
            raise SystemExit("PIN session created. Run the same command again after approval.")
        if args.auth_wait > 0:
            deadline = time.time() + args.auth_wait
            token = None
            while time.time() < deadline and not token:
                token = exchange_pin_for_token(session)
                if token:
                    break
                time.sleep(2)
            if not token:
                manual_hint = (
                    f" | Manual fallback: {session.link_url} (code: {session.manual_link_code})"
                    if session.manual_link_code
                    else ""
                )
                raise SystemExit(
                    f"PIN is not approved yet after waiting {args.auth_wait}s. "
                    f"Auth URL: {session.auth_url}{manual_hint}"
                )
        else:
            token = exchange_pin_for_token(session)
            if not token:
                manual_hint = (
                    f" | Manual fallback: {session.link_url} (code: {session.manual_link_code})"
                    if session.manual_link_code
                    else ""
                )
                raise SystemExit(
                    "PIN is not approved yet. Finish browser auth and run again. "
                    f"Auth URL: {session.auth_url}{manual_hint}"
                )
        print(token)
        return 0

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
