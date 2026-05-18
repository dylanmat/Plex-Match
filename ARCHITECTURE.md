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
Provides a local FastAPI interface backed only by cached data.

Suggested module: `plexmatch/web.py`

### Configuration Layer
Loads Plex token and optional settings from CLI flags, environment variables, and `.env` files.

Suggested module: `plexmatch/config.py`

### Cache Layer
Stores normalized users, watchlists, and local library items in project-local SQLite without storing credentials.

Suggested module: `plexmatch/cache.py`

### Comparison Service Layer
Builds cache-backed user rankings, comparisons, and random picks for both CLI-adjacent and web workflows.

Suggested module: `plexmatch/service.py`

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
Scores matches with simple deterministic V1 rules.

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
9. Missing cache state returns setup guidance instead of calling Plex APIs.

## Plex GraphQL Integration
- Endpoint target: Plex cloud/community GraphQL API.
- Expected behavior: authenticated Plex token can retrieve visible users/friends and watchlist hubs when privacy settings allow it.
- Required handling: pagination, missing fields, changed field names, empty responses, HTTP failures, and access-denied responses.
- GraphQL query text should be centralized and versioned in code or a `queries/` directory.

## V1 Scoring
- Base 100 points if the title appears in both watchlists.
- +10 if available on a configured local Plex server/library.
- +5 if IMDb/TMDb/Plex rating is >= 7.0, when available.
- -10 if either user has already watched it, where detectable.
- +5 if recently added, where detectable.

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
- Local FastAPI web UI reads cache only and does not access Plex tokens.
- Optional future TMDb, Trakt, Letterboxd, or IMDb import/enrichment.
