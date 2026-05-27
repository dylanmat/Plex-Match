# DECISIONS

## Purpose
Track architectural decisions, including why they were made and their long-term impact.

## ADR Template
Use this format for each new decision:
- Date:
- ID: ADR-000
- Status: Proposed | Accepted | Superseded | Deprecated
- Context:
- Decision:
- Consequences:
- Alternatives Considered:
- Supersedes/Superseded By:

## ADR Entries

### ADR-001 - Build a Local Python CLI First
- Date: 2026-05-17
- Status: Accepted
- Context: The goal is to prove watchlist comparison value quickly with minimal infrastructure.
- Decision: V1 will be a Python 3.11+ command-line tool with no web UI, database, hosted service, or OAuth flow.
- Consequences: Faster implementation, easier debugging, and lower security exposure. UX is limited to technical users initially.
- Alternatives Considered: Local web app, hosted app, browser extension.
- Supersedes/Superseded By: None

### ADR-002 - Use Plex Community GraphQL as the Primary Watchlist Source
- Date: 2026-05-17
- Status: Accepted
- Context: Plex watchlists are cloud/account-based and the local Plex Media Server does not expose a full per-server-user watchlist source.
- Decision: V1 will attempt to use Plex cloud/community GraphQL APIs to retrieve visible users/friends and watchlist hubs.
- Consequences: Enables the desired feature, but depends on undocumented/private API behavior that may change.
- Alternatives Considered: RSS feeds, user-provided exports, Trakt-only sync, local Plex server APIs.
- Supersedes/Superseded By: None

### ADR-003 - Normalize Before Matching
- Date: 2026-05-17
- Status: Accepted
- Context: Title-only matching can create false positives and misses across remakes, punctuation changes, and metadata providers.
- Decision: Normalize using Plex GUID, IMDb ID, TMDb ID, then title/year fallback.
- Consequences: More reliable matching when stable IDs exist, with acceptable fallback behavior when they do not.
- Alternatives Considered: Title-only matching, fuzzy matching first, external metadata enrichment first.
- Supersedes/Superseded By: None

### ADR-004 - Local Plex Availability Is Optional Enrichment
- Date: 2026-05-17
- Status: Accepted
- Context: Watchlist truth remains in Plex cloud/community APIs, but users may want to know whether a candidate is already present in their local Plex library.
- Decision: When `PLEX_SERVER_URL` and `PLEX_SERVER_TOKEN` are configured, PlexMatch checks local movie/show library sections and adds local availability to scoring and output.
- Consequences: Local availability improves movie-night selection without making the local server a required dependency. Failed local checks warn and continue with unknown availability.
- Alternatives Considered: Require local availability once configured, add an explicit CLI flag, or defer the check to a later cache/web UI milestone.
- Supersedes/Superseded By: None

### ADR-005 - Store Cache in the Project Workspace
- Date: 2026-05-17
- Status: Accepted
- Context: PlexMatch will eventually run from Docker, where a project-local or mounted path is easier to persist and inspect than an OS user cache directory.
- Decision: V2 stores normalized users, watchlists, and local library items in `.plexmatch/cache.sqlite3` by default, with `PLEXMATCH_CACHE_PATH` available for mounted Docker paths.
- Consequences: The cache is self-contained and portable. Cached metadata must be ignored by git and cleared with `--clear-cache` when needed.
- Alternatives Considered: OS-specific user cache directories, no cache path override, token-derived cache namespaces.
- Supersedes/Superseded By: None

### ADR-006 - Build a Cache-Only Local Web UI
- Date: 2026-05-17
- Status: Accepted
- Context: V3 needs a fast local movie-night interface while keeping Plex API calls and token handling out of web request paths.
- Decision: The local web UI uses FastAPI, binds to `127.0.0.1` by default, and reads only from the project-local SQLite cache.
- Consequences: Web views are fast and token-free, but users must populate or refresh cache through CLI commands before using the web UI.
- Alternatives Considered: Flask templates, stdlib HTTP server, web-triggered Plex API refreshes.
- Supersedes/Superseded By: None

### ADR-007 - Refresh Cache from CLI Scheduler
- Date: 2026-05-19
- Status: Accepted
- Context: The web UI should remain token-free, but expired cache entries should not make the interface unusable.
- Decision: Cache refresh is owned by CLI commands and a CLI scheduler loop. Expired cache entries remain readable as stale data until refreshed.
- Consequences: The security boundary stays clear: CLI/scheduler may read credentials, web reads SQLite only. Running the scheduler is recommended for long-lived web sessions.
- Alternatives Considered: Web-triggered refresh, manual-only refresh, deleting expired cache rows.
- Supersedes/Superseded By: None

### ADR-008 - Persist Plex Device Credentials for Token Refresh
- Date: 2026-05-26
- Status: Accepted
- Context: Plex JWTs expire, and repeatedly deleting/re-authorizing the `PlexMatch CLI` device is operationally noisy. Reusing an authorized Plex device requires retaining the local private key that matches the registered public JWK.
- Decision: PlexMatch stores temporary PIN state in `.plexmatch_pin_auth.json` and persistent reusable device credentials in `.plexmatch_device_auth.json`. `--auth-refresh` signs Plex nonces with the saved private key and exchanges the signed device JWT for a new Plex token.
- Consequences: Token renewal no longer requires browser approval while the saved device credentials and Plex authorized device remain valid. The device credential file is restricted local auth material and must stay ignored by git.
- Alternatives Considered: Always rerun PIN auth, write refreshed tokens into `.env` automatically, or make the web UI perform token refresh.
- Supersedes/Superseded By: None
