# ROADMAP

## Purpose
Track PlexMatch development priorities, sequencing, and delivery status.

## Completed

### v0.1.0 CLI MVP
- Goal: compare two Plex users' visible watchlists and show overlaps.
- Status: Complete
- Owner: Project Maintainer
- Dependencies: Plex token, Plex community/GraphQL access, visible friend/watchlist privacy settings.
- Success Criteria:
  - `--list-users` works.
  - Two selected users' watchlists can be fetched.
  - Overlaps are normalized and displayed.
  - `--random` selects one result.
  - `--format table|json` works.
  - Unit tests cover normalization, matching, and scoring.

### v0.1.32 CLI Hardening, Filtering, and Local Availability
- Goal: harden Plex API behavior, improve selection controls, and optionally identify local Plex library availability.
- Status: Complete
- Owner: Project Maintainer
- Dependencies: API exploration and sample response shapes.
- Success Criteria:
  - Queries are centralized.
  - Pagination is handled.
  - Missing or changed fields fail gracefully.
  - Debug mode helps inspect response shapes without exposing tokens.
  - Filter by movies, shows, or both.
  - Add runtime filter where metadata supports it.
  - Add rating filter where metadata supports it.
  - Add weighted random picker.
  - Exclude already watched where detectable.
  - Accept local Plex server URL and token.
  - Match local library items by GUID or metadata IDs.
  - Add availability to score and output.

### v0.2.0 Local Cache
- Goal: reduce repeated API calls and improve performance.
- Status: Complete
- Success Criteria:
  - SQLite cache.
  - Clear cache command.
  - Configurable retention.
  - No secrets stored in cache.

### v0.3.0 Local Web UI
- Goal: create a simple local movie-night interface.
- Status: Complete
- Success Criteria:
  - Flask or FastAPI app.
  - Select two users.
  - View ranked matches.
  - Reroll random pick.
  - Apply filters interactively.
  - Default view compares `self` against cached users.
  - Top users are ranked by total scored matches with `self`.
  - Results and random picks read from cache only.
  - CLI scheduler keeps expired cache entries refreshed while web remains cache-only.
  - Persistent Plex device auth supports token renewal without deleting the authorized device.

### v0.4.0 Auth, Scheduler, Docker, and Scoring
- Goal: improve long-running local operation, Docker deployment, and match scoring clarity.
- Status: Complete
- Success Criteria:
  - Successful PIN auth can update `.env` and trigger a one-shot cache refresh without printing tokens.
  - Saved device credentials support JWT renewal through `--auth-refresh`.
  - CLI-owned cache refresh commands and scheduler keep cache entries fresh while the web UI remains cache-only.
  - Docker image runs `python -m plexmatch`.
  - Compose can start the web UI on port 8000.
  - Compose can run ad hoc CLI commands.
  - Compose can run scheduler refresh loops.
  - Compose can run `ruff check .` and `pytest -q`.
  - Cache and Docker auth state persist on a documented mount.
  - Match scoring uses a capped 0-100% rating with watchlist alignment, wider support, local availability, and identity confidence.
  - Future scoring data collection needs are documented.

## Later

### v0.5.0 Metadata and Import Integrations
- Goal: improve matching and scoring beyond Plex metadata.
- Status: Planned
- Candidate Integrations:
  - Trakt
  - Letterboxd import
  - IMDb list import
  - TMDb enrichment
- Scoring Data Collection:
  - Critic, audience, Plex, TMDb, and IMDb ratings.
  - Runtime / duration.
  - Genres and mood tags.
  - Content rating.
  - Watchlist-added timestamp / recency.
  - Release date beyond year.
  - User watch history, progress, already-watched state, and vetoes.
  - External list/import signals from Trakt, Letterboxd, IMDb, or TMDb.
  - Streaming/provider availability beyond the local Plex library.

### v0.6.0 Hosted / Group Mode
- Goal: support multi-user watch parties and broader recommendations.
- Status: Future
- Candidate Features:
  - Hosted app
  - Voting
  - Veto list
  - Group sessions
  - Mood filters
  - Mobile-friendly UI
