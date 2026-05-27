import argparse
import importlib
import os
import sys
import time

from plexmatch.cache import CacheError, CacheStore
from plexmatch.matching import candidates, support_counts
from plexmatch.models import Item, User
from plexmatch.output import print_matches, print_users
from plexmatch.scoring import pick_random_match, score_candidates


REQUIRED_PACKAGES = ("httpx",)
OPTIONAL_PACKAGES = ("dotenv",)


def token_from_env_or_arg(arg_token: str | None) -> str:
    load_dotenv_if_available()
    token = (arg_token or os.getenv("PLEX_TOKEN") or "").strip()
    if not token:
        raise ValueError("Missing Plex token. Set PLEX_TOKEN in environment/.env or pass --token.")
    return token


def load_dotenv_if_available() -> None:
    if importlib.util.find_spec("dotenv"):
        dotenv = importlib.import_module("dotenv")
        dotenv.load_dotenv()


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
    p.add_argument(
        "--random",
        nargs="?",
        const="high",
        choices=["high", "low"],
        dest="random_mode",
        help="Pick one result. Use high for score-weighted selection or low for uniform selection.",
    )
    p.add_argument("--top", type=int)
    p.add_argument("--type", choices=["all", "movie", "show", "movies", "shows"], default="all")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.add_argument("--auth-pin", action="store_true", help="Start/poll Plex PIN+JWK auth flow and print JWT.")
    p.add_argument("--auth-refresh", action="store_true", help="Refresh a Plex JWT from saved device credentials and print it.")
    p.add_argument("--auth-reset", action="store_true", help="Delete local Plex PIN and device auth state, then exit unless --auth-pin is also used.")
    p.add_argument("--client-id", default="plexmatch-cli", help="Plex client identifier for PIN+JWK auth.")
    p.add_argument("--auth-wait", type=int, default=0, help="Seconds to poll for PIN approval before exiting.")
    p.add_argument("--no-cache", action="store_true", help="Bypass cache reads and writes for this run.")
    p.add_argument("--clear-cache", action="store_true", help="Delete local cache and exit.")
    p.add_argument("--cache-ttl-hours", type=float, help="Cache retention in hours. Defaults to PLEX_CACHE_TTL_HOURS or 6.")
    p.add_argument("--web", action="store_true", help="Start the local cache-backed web UI.")
    p.add_argument("--web-host", default="127.0.0.1", help="Host for the local web UI.")
    p.add_argument("--web-port", type=int, default=8000, help="Port for the local web UI.")
    p.add_argument("--refresh-cache", action="store_true", help="Refresh expired or missing cache entries once and exit.")
    p.add_argument("--cache-scheduler", action="store_true", help="Continuously refresh expired cache entries.")
    p.add_argument("--all", action="store_true", help="Refresh all known cache entries when used with --refresh-cache or --cache-scheduler.")
    p.add_argument("--scheduler-interval-minutes", type=float, default=15, help="Minutes between scheduler refresh checks.")
    args = p.parse_args()

    assert_runtime_dependencies()
    from plexmatch.api.graphql import PlexApi, PlexAuthError, PlexApiError

    load_dotenv_if_available()

    if args.clear_cache:
        try:
            CacheStore().clear()
        except CacheError as exc:
            raise SystemExit(str(exc))
        print("Cache cleared.")
        return 0

    if args.web:
        try:
            import uvicorn
        except ModuleNotFoundError as exc:
            raise SystemExit("Missing web dependencies. Run `pip install -r requirements.txt` and retry.") from exc
        uvicorn.run("plexmatch.web:create_app", factory=True, host=args.web_host, port=args.web_port)
        return 0

    if args.refresh_cache or args.cache_scheduler:
        token = token_from_env_or_arg(args.token)
        from plexmatch.refresh import refresh_once_with_auth_recovery, run_scheduler
        if args.cache_scheduler:
            if args.scheduler_interval_minutes <= 0:
                p.error("--scheduler-interval-minutes must be positive.")
            try:
                run_scheduler(token, interval_minutes=args.scheduler_interval_minutes, force=args.all)
            except ValueError as exc:
                raise SystemExit(str(exc))
            return 0
        try:
            _, stats = refresh_once_with_auth_recovery(token, force=args.all)
        except ValueError as exc:
            raise SystemExit(str(exc))
        print(stats.line())
        for message in stats.messages:
            print(message)
        return 0

    if args.auth_pin or args.auth_refresh or args.auth_reset:
        from plexmatch.api.auth import (
            PinAuthServiceError,
            PinAuthSessionExpired,
            clear_auth_state,
            device_auth_available,
            exchange_pin_for_token,
            load_pin_auth_session,
            refresh_token_from_device_auth,
            start_pin_auth,
        )

        if args.auth_reset:
            clear_auth_state()
            print("Plex auth state cleared. .env was not changed.")
            if not args.auth_pin:
                return 0

        if args.auth_refresh:
            try:
                print(refresh_token_from_device_auth())
            except PinAuthServiceError as exc:
                raise SystemExit(str(exc))
            return 0

        def print_pin_instructions(session, prefix: str = "Open this URL in a browser and sign in:") -> None:
            print(prefix)
            print(session.auth_url)
            print("Fallback URL if Plex Web cannot complete the request:")
            print(session.fallback_auth_url)
            if session.manual_link_code:
                print("If needed, open https://plex.tv/link and enter this 4-digit code:")
                print(session.manual_link_code)

        if device_auth_available():
            print("Saved Plex device credentials found. Use `--auth-refresh` to renew without browser approval.")
            print("Use `--auth-reset --auth-pin` only when the saved device should be replaced.")

        session = load_pin_auth_session()
        if session is None:
            session = start_pin_auth(args.client_id)
            print_pin_instructions(session)
            raise SystemExit("PIN session created. Run the same command again after approval.")
        if args.auth_wait > 0:
            deadline = time.time() + args.auth_wait
            token = None
            while time.time() < deadline and not token:
                try:
                    token = exchange_pin_for_token(session)
                except PinAuthSessionExpired as exc:
                    session = start_pin_auth(args.client_id)
                    print_pin_instructions(session, prefix=f"{exc} Open this new URL in a browser and sign in:")
                    raise SystemExit("PIN session recreated. Run the same command again after approval.")
                except PinAuthServiceError as exc:
                    raise SystemExit(str(exc))
                if token:
                    break
                time.sleep(2)
            if not token:
                manual_hint = (
                    f" | Fallback auth URL: {session.fallback_auth_url} | Manual fallback: {session.link_url} (code: {session.manual_link_code})"
                    if session.manual_link_code
                    else f" | Fallback auth URL: {session.fallback_auth_url}"
                )
                raise SystemExit(
                    f"PIN is not approved yet after waiting {args.auth_wait}s. "
                    f"Auth URL: {session.auth_url}{manual_hint}"
                )
        else:
            try:
                token = exchange_pin_for_token(session)
            except PinAuthSessionExpired as exc:
                session = start_pin_auth(args.client_id)
                print_pin_instructions(session, prefix=f"{exc} Open this new URL in a browser and sign in:")
                raise SystemExit("PIN session recreated. Run the same command again after approval.")
            except PinAuthServiceError as exc:
                raise SystemExit(str(exc))
            if not token:
                manual_hint = (
                    f" | Fallback auth URL: {session.fallback_auth_url} | Manual fallback: {session.link_url} (code: {session.manual_link_code})"
                    if session.manual_link_code
                    else f" | Fallback auth URL: {session.fallback_auth_url}"
                )
                raise SystemExit(
                    "PIN is not approved yet. Finish browser auth and run again. "
                    f"Auth URL: {session.auth_url}{manual_hint}"
                )
        print(token)
        return 0

    cache_ttl_seconds = parse_cache_ttl_seconds(args.cache_ttl_hours, p)
    cache = None if args.no_cache else CacheStore()
    token = token_from_env_or_arg(args.token)
    api = PlexApi(token)

    try:
        account_namespace = api.account_cache_key()
        if args.list_users:
            print_users(cached_users(api, cache, account_namespace, cache_ttl_seconds), args.format)
            return 0

        if not (args.user_a and args.user_b):
            p.error("Use --list-users or provide --user-a and --user-b.")

        users = cached_users(api, cache, account_namespace, cache_ttl_seconds)
        by_name = {u.title.lower(): u for u in users}
        self_user = next((u for u in users if u.is_self), None)
        if self_user is not None:
            by_name["self"] = self_user
            by_name["me"] = self_user
        try:
            a, b = by_name[args.user_a.lower()], by_name[args.user_b.lower()]
        except KeyError:
            raise SystemExit("One or both users are not accessible from this token. Use --list-users to see names, or use self/me for your own account.")

        normalized_type = {"movies": "movie", "shows": "show"}.get(args.type, args.type)
        items_a = cached_watchlist(api, cache, account_namespace, a.id, cache_ttl_seconds)
        items_b = cached_watchlist(api, cache, account_namespace, b.id, cache_ttl_seconds)
        candidate_items = candidates(items_a, items_b, normalized_type)
        availability = local_availability(candidate_items, cache, cache_ttl_seconds)
        other_watchlists = []
        selected_ids = {a.id, b.id}
        for user in users:
            if user.id in selected_ids:
                continue
            try:
                other_watchlists.append(cached_watchlist(api, cache, account_namespace, user.id, cache_ttl_seconds))
            except PlexApiError:
                continue
        found = score_candidates(
            candidate_items,
            support_counts(candidate_items, other_watchlists, normalized_type),
            availability,
        )
        if not found:
            raise SystemExit("No watchlist items found for the selected users and type.")
        if args.random_mode:
            found = [pick_random_match(found, args.random_mode)]
        print_matches(found, args.format, args.top)
    except (PlexAuthError, PlexApiError) as exc:
        raise SystemExit(str(exc))
    return 0


def parse_cache_ttl_seconds(arg_value: float | None, parser: argparse.ArgumentParser) -> int:
    raw_value = arg_value if arg_value is not None else os.getenv("PLEX_CACHE_TTL_HOURS", "6")
    try:
        hours = float(raw_value)
    except (TypeError, ValueError):
        parser.error("--cache-ttl-hours/PLEX_CACHE_TTL_HOURS must be a positive number.")
    if hours <= 0:
        parser.error("--cache-ttl-hours/PLEX_CACHE_TTL_HOURS must be a positive number.")
    return int(hours * 3600)


def cached_users(api, cache: CacheStore | None, namespace: str, ttl_seconds: int) -> list[User]:
    if cache is None:
        return api.users()
    try:
        cached = cache.get_users(namespace)
        if cached is not None:
            return cached
    except CacheError as exc:
        print(f"Warning: cache read skipped. {exc}", file=sys.stderr)
    users = api.users()
    try:
        cache.set_users(namespace, users, ttl_seconds)
    except CacheError as exc:
        print(f"Warning: cache write skipped. {exc}", file=sys.stderr)
    return users


def cached_watchlist(api, cache: CacheStore | None, namespace: str, user_id: str, ttl_seconds: int) -> list[Item]:
    if cache is None:
        return api.watchlist(user_id)
    try:
        cached = cache.get_watchlist(namespace, user_id)
        if cached is not None:
            return cached
    except CacheError as exc:
        print(f"Warning: cache read skipped. {exc}", file=sys.stderr)
    items = api.watchlist(user_id)
    try:
        cache.set_watchlist(namespace, user_id, items, ttl_seconds)
    except CacheError as exc:
        print(f"Warning: cache write skipped. {exc}", file=sys.stderr)
    return items


def local_availability(
    candidate_items: list[tuple[str, Item, str]],
    cache: CacheStore | None = None,
    ttl_seconds: int = 21600,
) -> dict[str, bool] | None:
    server_url = (os.getenv("PLEX_SERVER_URL") or "").strip()
    server_token = (os.getenv("PLEX_SERVER_TOKEN") or "").strip()
    if not (server_url and server_token):
        return None
    from plexmatch.api.local import LocalPlexApiError, availability_for_candidates

    try:
        local_items = cached_local_items(server_url, server_token, cache, ttl_seconds)
        return availability_for_candidates(candidate_items, local_items)
    except LocalPlexApiError as exc:
        print(f"Warning: local Plex availability check skipped. {exc}", file=sys.stderr)
        return None


def cached_local_items(
    server_url: str,
    server_token: str,
    cache: CacheStore | None,
    ttl_seconds: int,
) -> list[Item]:
    from plexmatch.api.local import LocalPlexApi

    if cache is None:
        return LocalPlexApi(server_url, server_token).library_items()
    try:
        cached = cache.get_local_items(server_url)
        if cached is not None:
            return cached
    except CacheError as exc:
        print(f"Warning: cache read skipped. {exc}", file=sys.stderr)
    items = LocalPlexApi(server_url, server_token).library_items()
    try:
        cache.set_local_items(server_url, items, ttl_seconds)
    except CacheError as exc:
        print(f"Warning: cache write skipped. {exc}", file=sys.stderr)
    return items
