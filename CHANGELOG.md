# CHANGELOG

All notable changes to PlexMatch should be documented here.

## [Unreleased]
- No unreleased changes.

## [0.1.5] - 2026-05-17
- Normalize provided Plex tokens by trimming leading/trailing whitespace before API use.
- Add additional Plex client headers (`X-Plex-Product`, `X-Plex-Version`, `X-Plex-Client-Identifier`, `Content-Type`) on GraphQL requests to improve compatibility with Plex auth checks.

## [0.1.4] - 2026-05-17
- Fix `401 Unauthorized` failures against `https://community.plex.tv/api` by retrying GraphQL requests with `Authorization: Bearer <token>` when `X-Plex-Token` auth is rejected.

## [0.1.3] - 2026-05-17
- Fix `python -m plexmatch --list-users` when `rich` is not installed by using a plain-text output fallback.
- Treat `rich` as optional at startup while keeping JSON and text output available.

## [0.1.1] - 2026-05-17
- Fix CLI startup when `python-dotenv` is not installed by making `.env` loading optional and continuing with normal environment variable lookup.

## [0.1.0] - 2026-05-17
- Implement first working CLI MVP under `plexmatch/` with token loading, user listing, watchlist retrieval, normalization, overlap detection, scoring, random selection, top slicing, type filtering, and table/JSON output.
- Add unit tests for normalization, matching, and scoring.
- Update README with V1 usage, security notes, and known API limitations.
