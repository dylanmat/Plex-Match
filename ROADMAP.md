# ROADMAP

## Purpose
Track PlexMatch development priorities, sequencing, and delivery status.

## Now

### V1 CLI MVP
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

### GraphQL Discovery and Hardening
- Goal: isolate and document Plex GraphQL query behavior.
- Status: Complete
- Owner: Project Maintainer
- Dependencies: API exploration and sample response shapes.
- Success Criteria:
  - Queries are centralized.
  - Pagination is handled.
  - Missing or changed fields fail gracefully.
  - Debug mode helps inspect response shapes without exposing tokens.

## Next

### V1.1 Filtering and Better Selection
- Goal: make results easier to use for movie-night decisions.
- Status: Complete
- Success Criteria:
  - Filter by movies, shows, or both.
  - Add runtime filter where metadata supports it.
  - Add rating filter where metadata supports it.
  - Add weighted random picker.
  - Exclude already watched where detectable.

### V1.2 Local Availability Check
- Goal: optionally identify whether a match is available on a configured local Plex server/library.
- Status: Complete
- Success Criteria:
  - Accept local Plex server URL and token.
  - Match local library items by GUID or metadata IDs.
  - Add availability to score and output.

## Later

### V2 Local Cache
- Goal: reduce repeated API calls and improve performance.
- Status: Planned
- Success Criteria:
  - SQLite cache.
  - Clear cache command.
  - Configurable retention.
  - No secrets stored in cache.

### V3 Local Web UI
- Goal: create a simple local movie-night interface.
- Status: Planned
- Success Criteria:
  - Flask or FastAPI app.
  - Select two users.
  - View ranked matches.
  - Reroll random pick.
  - Apply filters interactively.

### V4 Metadata and Import Integrations
- Goal: improve matching and scoring beyond Plex metadata.
- Status: Planned
- Candidate Integrations:
  - Trakt
  - Letterboxd import
  - IMDb list import
  - TMDb enrichment

### V5 Hosted / Group Mode
- Goal: support multi-user watch parties and broader recommendations.
- Status: Future
- Candidate Features:
  - Hosted app
  - Voting
  - Veto list
  - Group sessions
  - Mood filters
  - Mobile-friendly UI
