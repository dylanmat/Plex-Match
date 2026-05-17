# PlexMatch

## Overview
PlexMatch is a Python command-line tool for comparing two Plex users' watchlists and selecting something both people want to watch.

V1 uses a Plex community/GraphQL approach, normalizes entries by stable IDs, finds overlap, scores matches, and can randomly pick one title.

## Version
Current version: `0.1.9`

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


## Authentication (Plex JWT Recommended)
- Plex now recommends JWT auth with short-lived (7 day) tokens and per-device key registration.
- PlexMatch currently accepts a token via `--token` or `PLEX_TOKEN`; JWT tokens work in the same `X-Plex-Token` header path as legacy tokens.
- For new apps, prefer PIN + JWK registration (`POST https://clients.plex.tv/api/v2/pins`) then exchange with a device-signed JWT.
- For existing legacy-token apps, register JWK at `POST https://clients.plex.tv/api/v2/auth/jwk`, then use nonce + signed device JWT refresh flow (`/auth/nonce` then `/auth/token`).
- Plan for token refresh every 7 days. If token validation fails (for example, expired token), obtain a fresh JWT and rerun.

## Security Notes
- Never commit tokens or `.env` files.
- Plex tokens are never printed by CLI output.
- Errors are written without secrets.

## Known API Limitations
- Plex community/GraphQL APIs are undocumented/private and may change fields/endpoints.
- Query shapes may differ by account privacy or Plex backend rollout.
- Some IDs or media types may be missing, triggering fallback matching.


## Changelog
- 0.1.9: Documented Plex JWT authentication guidance (PIN/JWK registration, nonce refresh flow, and 7-day token rotation expectations).
- 0.1.8: Aligned Plex API access flow with watchlistarr-style endpoints (friends GraphQL + discover watchlist pagination) and improved Plex headers.
- 0.1.7: Updated `test_api.py` to test GraphQL connectivity with the same headers/auth fallback used by the main client.
- 0.1.5: Added token trimming and extra Plex client headers to reduce avoidable 401 responses.
- 0.1.4: Retried GraphQL auth with `Authorization: Bearer <token>` when token header auth is rejected.
- 0.1.3: Made rich optional at runtime with plain-text fallback output for environments missing `rich`.
- 0.1.2: Added startup dependency checks with clear installation guidance for missing modules.
