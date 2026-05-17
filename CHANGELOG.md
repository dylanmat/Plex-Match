## [0.1.2] - 2026-05-17
- Added CLI startup validation for required runtime packages before importing API modules.
- Improved missing dependency error message to explicitly recommend `pip install -r requirements.txt`.

# CHANGELOG

All notable changes to PlexMatch should be documented here.

## [Unreleased]
- No unreleased changes.

## [0.1.1] - 2026-05-17
- Fix CLI startup when `python-dotenv` is not installed by making `.env` loading optional and continuing with normal environment variable lookup.

## [0.1.0] - 2026-05-17
- Implement first working CLI MVP under `plexmatch/` with token loading, user listing, watchlist retrieval, normalization, overlap detection, scoring, random selection, top slicing, type filtering, and table/JSON output.
- Add unit tests for normalization, matching, and scoring.
- Update README with V1 usage, security notes, and known API limitations.
