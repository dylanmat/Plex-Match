# PlexMatch

## Overview
PlexMatch is a Python tool for comparing Plex users' watchlists and selecting something both people want to watch.

It uses a Plex community/GraphQL approach, normalizes entries by stable IDs, finds overlap, scores matches, and can randomly pick one title. The CLI populates a local cache, and the local web UI reads from that cache for fast movie-night browsing.

## Version
Current version: `0.3.0`

## Features
- PIN + JWK auth bootstrap flow (`--auth-pin`) to obtain a Plex JWT without legacy token
- Python 3.11+ CLI (`python -m plexmatch`)
- Token input from `--token` or `PLEX_TOKEN` (`.env` supported)
- List accessible users/friends (`--list-users`)
- Fetch watchlists for two selected users
- Normalize by GUID, IMDb, TMDb, then title/year fallback
- Match overlaps and deterministic scoring
- Diagnostic comparison output lists all filtered watchlist items with source labels (`both`, `user_a`, `user_b`)
- Output as table or JSON
- Filters and selection flags: `--type`, `--top`, `--random high`, `--random low`
- Optional local Plex server availability check using `PLEX_SERVER_URL` and `PLEX_SERVER_TOKEN`
- Project-local SQLite cache with `--no-cache`, `--clear-cache`, and configurable TTL
- Local FastAPI web UI (`--web`) that reads only from cache

## CLI Examples
```bash
python -m plexmatch --auth-pin
python -m plexmatch --auth-pin --auth-wait 90
python -m plexmatch --list-users
python -m plexmatch --user-a self --user-b "Joy"
python -m plexmatch --user-a "Dylan" --user-b "Joy"
python -m plexmatch --user-a "Dylan" --user-b "Joy" --type movies --top 10
python -m plexmatch --user-a "Dylan" --user-b "Joy" --random
python -m plexmatch --user-a "Dylan" --user-b "Joy" --random low
python -m plexmatch --user-a "Dylan" --user-b "Joy" --format json
python -m plexmatch --clear-cache
python -m plexmatch --user-a "Dylan" --user-b "Joy" --no-cache
python -m plexmatch --web
```

## Quickstart
1. Create env: `python -m venv .venv`
2. Activate env and install: `pip install -r requirements.txt`
3. Create `.env` with: `PLEX_TOKEN=your_token_here`
4. List users: `python -m plexmatch --list-users`
5. Compare users: `python -m plexmatch --user-a "User A" --user-b "User B"`
6. Run checks: `ruff check . && pytest -q`

## Local Availability Check
When both `PLEX_SERVER_URL` and `PLEX_SERVER_TOKEN` are configured, PlexMatch automatically checks movie/show library sections on the local Plex server and marks comparison results as locally available, unavailable, or unknown.

```env
PLEX_SERVER_URL=http://localhost:32400
PLEX_SERVER_TOKEN=your_local_server_token_here
```

```bash
python -m plexmatch --user-a "Dylan" --user-b "Joy" --type movies
```

Available local items receive a +10 score bonus. If the local server is unreachable or rejects the token, PlexMatch prints a sanitized warning and continues with local availability marked unknown.

## Local Cache
PlexMatch caches normalized users, watchlists, and local library items in `.plexmatch/cache.sqlite3` by default. The cache is self-contained for future Docker use and `.plexmatch/` is ignored by git.

```env
PLEX_CACHE_TTL_HOURS=6
PLEX_USERS_CACHE_TTL_HOURS=6
PLEX_WATCHLIST_CACHE_TTL_HOURS=6
PLEX_LOCAL_CACHE_TTL_HOURS=24
PLEXMATCH_CACHE_PATH=.plexmatch/cache.sqlite3
```

```bash
python -m plexmatch --user-a "Dylan" --user-b "Joy"
python -m plexmatch --user-a "Dylan" --user-b "Joy" --cache-ttl-hours 1
python -m plexmatch --user-a "Dylan" --user-b "Joy" --no-cache
python -m plexmatch --clear-cache
```

For Docker, mount `.plexmatch/` or set `PLEXMATCH_CACHE_PATH` to a mounted path such as `/app/.plexmatch/cache.sqlite3`. Tokens are not stored in the cache.

## Cache Refresh Scheduler
The web UI is cache-only, so use the CLI scheduler to keep cache entries fresh without exposing tokens to web handlers.

```bash
python -m plexmatch --refresh-cache
python -m plexmatch --refresh-cache --all
python -m plexmatch --cache-scheduler
python -m plexmatch --cache-scheduler --scheduler-interval-minutes 15
```

`--refresh-cache` updates only expired or missing entries. `--all` refreshes all known users/watchlists and local library data. Users and watchlists default to 6-hour TTLs; local library availability defaults to 24 hours. Expired entries remain visible as stale data until the scheduler refreshes them.

## Local Web UI
The web UI is cache-only by design. Populate cache with CLI commands first, then start the local server:

```bash
python -m plexmatch --list-users
python -m plexmatch --user-a self --user-b "Friend Name"
python -m plexmatch --web
```

Open `http://127.0.0.1:8000`. The default view compares `self` against cached users, ranks users by total scored matches, and supports media filters plus low-confidence and high-confidence random picks. Web results are memoized in memory and refresh automatically when the SQLite cache file changes. If cache entries expire, stale results remain visible with a warning while the CLI scheduler refreshes them. Use `--web-host` and `--web-port` when running in Docker or another local environment.


## Authentication (Plex JWT Recommended)
- Plex now recommends JWT auth with short-lived (7 day) tokens and per-device key registration.
- PlexMatch currently accepts a token via `--token` or `PLEX_TOKEN`; JWT tokens work in the same `X-Plex-Token` header path as legacy tokens.
- After `python -m plexmatch --auth-pin` succeeds, save the printed JWT into `PLEX_TOKEN` or pass it with `--token`.
- For new apps, prefer PIN + JWK registration (`POST https://clients.plex.tv/api/v2/pins`) then exchange with a device-signed JWT that includes the registered JWK `kid` header.
- For existing legacy-token apps, register JWK at `POST https://clients.plex.tv/api/v2/auth/jwk`, then use nonce + signed device JWT refresh flow (`/auth/nonce` then `/auth/token`).
- Plan for token refresh every 7 days. If token validation fails (for example, expired token), obtain a fresh JWT and rerun.

## Security Notes
- Never commit tokens or `.env` files.
- Plex tokens are never printed by CLI output.
- Errors are written without secrets.

## Known API Limitations
- Plex community/GraphQL APIs are undocumented/private and may change fields/endpoints.
- Query shapes may differ by account privacy or Plex backend rollout.
- Some IDs or media types may be missing, triggering fallback matching.


## Changelog
- Unreleased: Add CLI-owned cache scheduler and stale-cache web fallback.
- 0.3.0: Add cache-only FastAPI web UI for ranked self comparisons and random picks.
- 0.2.0: Add project-local SQLite caching for users, watchlists, and local library items.
- 0.1.32: Add optional local Plex server availability enrichment and scoring/output support.
- 0.1.31: Normalize one-sided candidate base scores so `user_a` and `user_b` both start at 10 before support bonuses.
- 0.1.30: Tighten high-confidence random selection to exclude low-score recommendations and sample only from the higher-scored tier.
- 0.1.29: Add high-confidence score-weighted random selection and low-confidence uniform random selection.
- 0.1.28: Add cross-user support scoring: each other accessible user with a candidate item in their watchlist adds +5 to that item's score.
- 0.1.27: Improve watchlist matching when friend items lack years by matching unique same-title entries if one side is missing the year, and request richer friend watchlist fields where Plex allows them.
- 0.1.26: List and score all filtered watchlist candidates instead of suppressing one-sided items when no strict overlaps are detected.
- 0.1.25: Merge Plex XML friends with `allFriendsV2` so friend watchlist lookups use community GraphQL IDs while account IDs remain visible.
- 0.1.24: Use friend UUIDs for friend watchlist GraphQL while showing numeric Plex account IDs as separate user metadata.
- 0.1.23: Use numeric Plex friend IDs from `--list-users` for friend watchlist GraphQL and sanitize GraphQL `data: null` responses.
- 0.1.22: Reduce self-watchlist page size for Plex provider compatibility and fall back from Discover to Metadata provider watchlist endpoints.
- 0.1.21: Move Discover watchlist auth out of query strings, add PlexAPI-compatible watchlist request flags, and sanitize Discover 400/401 failures.
- 0.1.20: Include the signed-in Plex account as `self` in `--list-users` and route `--user-a self`/`me` through the Discover watchlist endpoint.
- 0.1.19: Use Plex's XML user-sharing API for `--list-users` and replace raw 401 tracebacks with sanitized token guidance.
- 0.1.18: Align PIN auth URLs and JWT payloads with PlexAPI's current OAuth helper so Plex displays `PlexMatch` instead of `0` and receives nonce/scope claims.
- 0.1.17: Fix PIN auth exchange by signing device JWTs with the registered JWK `kid`, replacing expired/old PIN sessions, and sanitizing auth HTTP errors.
- 0.1.16: Fix PIN auth link routing by restoring hash-based `https://app.plex.tv/auth#!?...` format so browser approval completes instead of stalling on the Plex logo screen.
- 0.1.13: Added a manual PIN fallback (`https://plex.tv/link` + code) for cases where `app.plex.tv/auth` returns a sign-in completion error.
- 0.1.12: Improved PIN auth UX by adding `--auth-wait` polling support and by printing the auth URL when approval is still pending.
- 0.1.11: Added community GraphQL endpoint fallback (`/api` then `/api/v2`) for improved Plex JWT compatibility when listing users.
- 0.1.10: Added Option 1 PIN+JWK authentication flow in CLI (`--auth-pin`) to bootstrap Plex JWT tokens.
- 0.1.9: Documented Plex JWT authentication guidance (PIN/JWK registration, nonce refresh flow, and 7-day token rotation expectations).
- 0.1.8: Aligned Plex API access flow with watchlistarr-style endpoints (friends GraphQL + discover watchlist pagination) and improved Plex headers.
- 0.1.7: Updated `test_api.py` to test GraphQL connectivity with the same headers/auth fallback used by the main client.
- 0.1.5: Added token trimming and extra Plex client headers to reduce avoidable 401 responses.
- 0.1.4: Retried GraphQL auth with `Authorization: Bearer <token>` when token header auth is rejected.
- 0.1.3: Made rich optional at runtime with plain-text fallback output for environments missing `rich`.
- 0.1.2: Added startup dependency checks with clear installation guidance for missing modules.
