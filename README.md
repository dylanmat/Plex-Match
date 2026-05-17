# PlexMatch

## Overview
PlexMatch is a Python command-line tool for comparing two Plex users' watchlists and selecting something both people want to watch.

The initial version uses Plex's cloud/community GraphQL interface to retrieve accessible watchlists for users/friends visible to the authenticated Plex account. It then normalizes titles, finds overlaps, scores matches, and can randomly select a result.

This project intentionally starts as a local CLI tool. No hosted service, web UI, OAuth flow, or database is required for V1.

## Audience
- Plex power users who want an easier way to pick a movie or show with another person.
- Developers experimenting with Plex watchlist metadata.
- Future maintainers who may extend the tool into a local web app or hosted service.

## Core Capabilities
- Authenticate with a Plex token supplied by CLI argument, environment variable, or `.env` file.
- Retrieve accessible Plex users/friends and their watchlists through Plex community/GraphQL APIs.
- Compare two users' watchlists and identify overlapping movies or shows.
- Normalize entries using stable IDs where available: Plex GUID, IMDb ID, TMDb ID, then title/year fallback.
- Score results and display them in a readable CLI table or JSON output.
- Randomly select a matching title for movie-night decisions.

## V1 CLI Examples
```powershell
python -m plexmatch --list-users

python -m plexmatch --user-a "Dylan" --user-b "Joy"

python -m plexmatch --user-a "Dylan" --user-b "Joy" --random

python -m plexmatch --user-a "Dylan" --user-b "Joy" --top 10

python -m plexmatch --user-a "Dylan" --user-b "Joy" --type movies

python -m plexmatch --user-a "Dylan" --user-b "Joy" --format json
```

## Quickstart
1. Create env: `python -m venv .venv`
2. Activate on Windows: `.venv\Scripts\Activate.ps1`
3. Install: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`
5. Add your Plex token as `PLEX_TOKEN=...`
6. List visible users: `python -m plexmatch --list-users`
7. Compare two watchlists: `python -m plexmatch --user-a "User A" --user-b "User B"`
8. Run tests: `pytest -q`

## Important Caveat
Plex's GraphQL/community API appears to be undocumented/private. It may change without notice. The code should isolate GraphQL calls behind a small API layer and handle missing or changed fields gracefully.

## Documentation Map
- Context and goals: `CONTEXT.md`
- Architecture and data flow: `ARCHITECTURE.md`
- Security expectations: `SECURITY.md`
- Coding/testing/review standards: `STANDARDS.md`
- Decision history: `DECISIONS.md`
- Planned milestones: `ROADMAP.md`
- Release notes: `CHANGELOG.md`
- AI agent workflow: `AGENTS.md`
