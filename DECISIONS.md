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
