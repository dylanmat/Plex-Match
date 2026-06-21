# ARCHITECTURE

## Architecture Principles
- Keep Plex-specific API behavior behind clear interfaces.
- Prefer small modules with narrow responsibilities.
- Make CLI output useful without hiding debug details when requested.
- Degrade gracefully when Plex fields, IDs, ratings, or watch-state fields are missing.
- Treat Plex GraphQL behavior as unstable and document assumptions.

## Component Model

### CLI Layer
Responsible for argument parsing, environment loading, command routing, user-facing output, and exit codes.

Suggested module: `plexmatch/cli.py`

### Web UI Layer
Provides a local FastAPI interface backed by cached comparison data and a local-only reauthorization control surface.

Suggested module: `plexmatch/web.py`

### Configuration Layer
Loads Plex token and optional settings from CLI flags, environment variables, and `.env` files.

Suggested module: `plexmatch/config.py`

### Authentication Layer
Owns Plex PIN/JWK bootstrap, generated per-device client identifiers, saved device credentials, nonce signing, and token refresh for CLI and scheduler commands.

Suggested module: `plexmatch/api/auth.py`

### Cache Layer
Stores normalized users, watchlists, and local library items in project-local SQLite without storing credentials.

Suggested module: `plexmatch/cache.py`

### Comparison Service Layer
Builds cache-backed user rankings, comparisons, and random picks for both CLI-adjacent and web workflows.

Suggested module: `plexmatch/service.py`

### Refresh Scheduler Layer
Refreshes expired cache entries from the CLI side while preserving the web UI token disclosure boundary.

Suggested module: `plexmatch/refresh.py`

### Plex API Layer
Encapsulates Plex community/GraphQL calls. This should be the only layer aware of endpoint URLs, GraphQL query documents, pagination mechanics, headers, and raw response shapes.

Suggested modules:
- `plexmatch/api/graphql.py`
- `plexmatch/api/local.py`
- `plexmatch/api/users.py`
- `plexmatch/api/watchlists.py`

### Domain Model Layer
Defines normalized user, watchlist, and media item models. Use dataclasses or Pydantic models.

Suggested module: `plexmatch/models.py`

### Normalization Layer
Builds stable match keys from Plex GUID, IMDb ID, TMDb ID, and title/year fallback.

Suggested module: `plexmatch/normalize.py`

### Matching Layer
Finds overlaps, resolves duplicates, and produces match records.

Suggested module: `plexmatch/matching.py`

### Scoring Layer
Scores matches with deterministic capped 0-100% rules.

Suggested module: `plexmatch/scoring.py`

### Output Layer
Formats table and JSON output. Table output should use `rich` or `tabulate`.

Suggested module: `plexmatch/output.py`

## Inference and Data Flow
1. User runs CLI or local web command.
2. CLI loads config and validates token presence.
3. API layer validates Plex authentication.
4. Cache layer returns fresh normalized data when available.
5. For `--list-users`, API layer retrieves accessible users/friends on cache miss and output layer displays them.
6. For comparison commands, API layer fetches watchlists for selected users on cache miss.
7. Normalization layer converts raw items into stable normalized media records.
8. Matching layer finds overlaps between both users.
9. If local Plex server settings are configured, local library items are fetched or read from cache and matched to candidates.
10. Scoring layer assigns scores.
11. Output layer prints table or JSON.
12. If `--random` is used, selector chooses one item from scored matches.

## Web UI Data Flow
1. User starts `python -m plexmatch --web`.
2. FastAPI app binds to `127.0.0.1:8000` unless overridden.
3. Web service reads users, watchlists, and local library items from `.plexmatch/cache.sqlite3` or `PLEXMATCH_CACHE_PATH`.
4. Web service builds an in-process snapshot and invalidates it when the SQLite cache file modification time changes.
5. Cached `self` is compared against cached users.
6. Users are ranked by total scored matches against `self`.
7. Selected comparison results are memoized by user and media type, then filtered and randomized from cache only.
8. The frontend fetches ranked users on initial load or media-type changes; selecting a user only fetches that comparison.
9. Expired cache entries are shown as stale data instead of being deleted.
10. Missing cache state returns setup guidance instead of calling Plex APIs.
11. A local browser may initiate Plex PIN/JWK reauthorization only when `PLEX_TOKEN` is an expired JWT; the web response contains only approval URLs and coarse auth/cache status.
12. The server-side auth controller performs PIN exchange, `.env` token update, and one-shot cache refresh without returning token material to the browser.

## Cache Refresh Flow
1. User runs `python -m plexmatch --refresh-cache` or keeps `--cache-scheduler` running.
2. CLI/scheduler reads Plex credentials from `.env` or environment.
3. Scheduler checks cache metadata and refreshes only expired or missing entries.
4. Users and watchlists default to 6-hour TTLs; local library defaults to 24 hours.
5. Failed individual refreshes keep stale data and continue with sanitized warnings.
6. If Plex rejects `PLEX_TOKEN`, the scheduler can use saved device credentials to refresh the token in memory and continue.
7. The scheduler prints guidance to run `--auth-refresh` and update `.env`; it does not write tokens automatically.
8. Web UI observes the updated SQLite file mtime and rebuilds its in-memory snapshot.

## Authentication Flow
1. `--auth-pin` creates a temporary PIN session with a generated Plex client identifier unless `--client-id` is provided, then registers a device public JWK with Plex.
2. After browser approval, PlexMatch signs a nonce with the matching private key and exchanges the PIN for a Plex JWT.
3. Successful PIN exchange saves persistent device credentials in `.plexmatch_device_auth.json`, updates `PLEX_TOKEN` in `.env` without printing the token, and deletes only temporary PIN state.
4. After successful PIN exchange, the CLI starts a one-shot cache refresh with the fresh in-memory token.
5. `--auth-refresh` signs a fresh Plex nonce with the saved private key and exchanges it at `/auth/token` for a new JWT using Plex's current `jwt` request body.
6. `--auth-reset` deletes temporary and persistent local auth state but does not edit `.env`.

## Plex GraphQL Integration
- Endpoint target: Plex cloud/community GraphQL API.
- Expected behavior: authenticated Plex token can retrieve visible users/friends and watchlist hubs when privacy settings allow it.
- Required handling: pagination, missing fields, changed field names, empty responses, HTTP failures, and access-denied responses.
- GraphQL query text should be centralized and versioned in code or a `queries/` directory.

## Match Scoring
PlexMatch scores true overlaps and one-sided recommendations on a capped 0-100% scale using only currently collected data:
- Watchlist alignment: 50 points when both selected users have the title, or 20 points when only one selected user has it.
- Wider group support: up to 20 points, calculated as `round(20 * support_count / other_watchlist_count)`.
- Local availability: 20 points when available locally, 0 when unavailable, and 10 neutral points when local availability is unknown or not configured.
- Match confidence: 10 points for GUID/IMDb/TMDb keys, 7 for title plus year fallback, and 4 for title-only or missing-year fallback.

Scores are capped at 100%. The public `Match.score` field remains an integer, now interpreted as a percentage.

## Evaluation and Quality Gates
Minimum V1 acceptance checks:
- `ruff check .`
- `pytest -q`
- Unit tests for normalization.
- Unit tests for overlap detection.
- Unit tests for scoring.
- Manual smoke test for `--list-users`.
- Manual smoke test for two-user comparison.

## Operational Integration Points
- Plex token loaded from local environment only.
- Optional local Plex server availability checks through `PLEX_SERVER_URL` and `PLEX_SERVER_TOKEN`.
- Project-local SQLite cache at `.plexmatch/cache.sqlite3` by default, overrideable with `PLEXMATCH_CACHE_PATH`.
- Docker image entrypoint is `python -m plexmatch`; Compose exposes web, scheduler, ad hoc CLI, and test services.
- Docker Compose stores cache plus container auth state under the mounted `.plexmatch/` directory with `PLEXMATCH_CACHE_PATH`, `PLEXMATCH_PIN_AUTH_PATH`, and `PLEXMATCH_DEVICE_AUTH_PATH`.
- Local FastAPI web UI reads cache only for comparison data and does not expose Plex tokens.
- Local-only web reauthorization may update `.env` and refresh cache from server-side auth code when `PLEX_TOKEN` is expired, but final tokens and device secrets must not be returned to browser clients.
- CLI scheduler owns cache refresh and is allowed to read Plex credentials.
- Persistent Plex device credentials are local CLI/scheduler auth artifacts and are ignored by git.
- Optional future TMDb, Trakt, Letterboxd, or IMDb import/enrichment.
