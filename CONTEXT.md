# CONTEXT

## System Purpose
PlexMatch helps two Plex users choose what to watch by comparing their Plex watchlists, finding overlap, scoring the matches, and optionally selecting one at random.

## Users & Stakeholders
- Primary users: Plex users who share watchlist visibility with one another.
- Technical owner: project maintainer/developer.
- Adjacent dependencies: Plex cloud/community APIs, Plex account privacy settings, optional future metadata providers such as TMDb or Trakt.

## Operational Context
- Runtime environments: local developer workstation, initially Windows-friendly but cross-platform Python where practical.
- Interface: command line only for V1.
- External integrations: Plex community/GraphQL API, optional local Plex server availability check in a later V1/V2 increment.
- Technical constraints: Plex watchlists are cloud/account-based and are not stored directly on the local Plex Media Server.
- Compliance constraints: no credentials committed to source control; no tokens in logs, prompts, screenshots, or issue text.

## Domain Vocabulary
- Plex token: authentication token used to call Plex services.
- Community API: Plex cloud endpoint used by Plex social/watchlist features.
- GraphQL operation: Plex cloud query used to retrieve users and watchlist hubs.
- Watchlist item: movie, show, or other Plex metadata entry saved by a user.
- Normalized key: stable matching identifier created from Plex GUID, IMDb ID, TMDb ID, or title/year fallback.
- Overlap: title that appears in both selected users' watchlists.
- Weighted random: random selection where higher-scored matches are more likely to be selected.

## Current State
- What exists today: project prompt and root documentation template.
- Known limitations: Plex's GraphQL/community API is likely undocumented/private and may break.
- Active risks: API field changes, pagination changes, privacy restrictions, inaccessible watchlists, incomplete metadata, duplicate titles, title/year collisions.

## Success Signals
- `--list-users` returns accessible Plex users/friends without exposing secrets.
- Comparing two visible users returns a deterministic overlap list.
- `--random` selects one valid overlap.
- Empty, private, or inaccessible watchlists produce clear error messages.
- Tests cover normalization, overlap detection, and scoring.

## Guardrails
- Do not log Plex tokens or other secrets.
- Do not require Plex passwords.
- Do not scrape credentials from browsers or local Plex config.
- Do not depend on local Plex Media Server user lists as the source of watchlist truth.
- Keep GraphQL assumptions isolated and documented.

## Pointers
- High-level overview: `README.md`
- System design/details: `ARCHITECTURE.md`
- Security expectations: `SECURITY.md`
- Coding/testing/review conventions: `STANDARDS.md`
- Decision history: `DECISIONS.md`
