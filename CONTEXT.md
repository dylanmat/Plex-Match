# CONTEXT

## System Purpose
PlexMatch helps Plex users choose what to watch by comparing watchlists, finding overlap, scoring matches, and selecting recommendations from either the CLI or a local cache-backed web UI.

## Users & Stakeholders
- Primary users: Plex users who share watchlist visibility with one another.
- Technical owner: project maintainer/developer.
- Adjacent dependencies: Plex cloud/community APIs, Plex account privacy settings, optional future metadata providers such as TMDb or Trakt.

## Operational Context
- Runtime environments: local developer workstation and future Docker container.
- Interface: command line plus local FastAPI web UI.
- External integrations: Plex community/GraphQL API and optional local Plex server availability checks through the CLI/cache population path.
- Technical constraints: Plex watchlists are cloud/account-based and are not stored directly on the local Plex Media Server.
- Compliance constraints: no credentials committed to source control; no tokens in logs, prompts, screenshots, or issue text.

## Domain Vocabulary
- Plex token: authentication token used to call Plex services (legacy token or new 7-day JWT).
- Community API: Plex cloud endpoint used by Plex social/watchlist features.
- GraphQL operation: Plex cloud query used to retrieve users and watchlist hubs.
- Watchlist item: movie, show, or other Plex metadata entry saved by a user.
- Normalized key: stable matching identifier created from Plex GUID, IMDb ID, TMDb ID, or title/year fallback.
- Overlap: title that appears in both selected users' watchlists.
- Weighted random: random selection where higher-scored matches are more likely to be selected.

## Current State
- What exists today: Python CLI with Plex watchlist comparison, filtering, scoring, random selection, cross-user support scoring, optional local Plex server availability enrichment, project-local SQLite cache, and cache-only local web UI.
- Known limitations: Plex's GraphQL/community API is likely undocumented/private and may break.
- Active risks: API field changes, pagination changes, privacy restrictions, inaccessible watchlists, incomplete metadata, duplicate titles, title/year collisions, and JWT expiry/refresh handling drift.

## Success Signals
- `--list-users` returns accessible Plex users/friends without exposing secrets.
- Comparing two visible users returns a deterministic overlap list.
- `--random` selects one valid overlap.
- Configured local Plex server checks identify whether candidates are already available locally.
- The local web UI loads quickly from cache and shows ranked users compared to `self`.
- Empty, private, or inaccessible watchlists produce clear error messages.
- Tests cover normalization, overlap detection, and scoring.

## Guardrails
- Do not log Plex tokens or other secrets.
- Do not require Plex passwords.
- Do not scrape credentials from browsers or local Plex config.
- Do not depend on local Plex Media Server user lists as the source of watchlist truth.
- Keep GraphQL assumptions isolated and documented.
- Keep the web UI cache-only; it must not read or require Plex tokens.

## Pointers
- High-level overview: `README.md`
- System design/details: `ARCHITECTURE.md`
- Security expectations: `SECURITY.md`
- Coding/testing/review conventions: `STANDARDS.md`
- Decision history: `DECISIONS.md`
