# PlexMatch

## Overview
PlexMatch is a Python command-line tool for comparing two Plex users' watchlists and selecting something both people want to watch.

V1 uses a Plex community/GraphQL approach, normalizes entries by stable IDs, finds overlap, scores matches, and can randomly pick one title.

## Version
Current version: `0.1.2`

## Features (V1)
- Python 3.11+ CLI only (`python -m plexmatch`)
- Token input from `--token` or `PLEX_TOKEN` (`.env` supported)
- List accessible users/friends (`--list-users`)
- Fetch watchlists for two selected users
- Normalize by GUID, IMDb, TMDb, then title/year fallback
- Match overlaps and deterministic scoring
- Output as table or JSON
- Filters and selection flags: `--type`, `--top`, `--random`

## CLI Examples
```bash
python -m plexmatch --list-users
python -m plexmatch --user-a "Dylan" --user-b "Joy"
python -m plexmatch --user-a "Dylan" --user-b "Joy" --type movies --top 10
python -m plexmatch --user-a "Dylan" --user-b "Joy" --random
python -m plexmatch --user-a "Dylan" --user-b "Joy" --format json
```

## Quickstart
1. Create env: `python -m venv .venv`
2. Activate env and install: `pip install -r requirements.txt`
3. Create `.env` with: `PLEX_TOKEN=your_token_here`
4. List users: `python -m plexmatch --list-users`
5. Compare users: `python -m plexmatch --user-a "User A" --user-b "User B"`
6. Run checks: `ruff check . && pytest -q`

## Security Notes
- Never commit tokens or `.env` files.
- Plex tokens are never printed by CLI output.
- Errors are written without secrets.

## Known API Limitations
- Plex community/GraphQL APIs are undocumented/private and may change fields/endpoints.
- Query shapes may differ by account privacy or Plex backend rollout.
- Some IDs or media types may be missing, triggering fallback matching.


## Changelog
- 0.1.2: Added startup dependency checks with clear installation guidance for missing modules.
