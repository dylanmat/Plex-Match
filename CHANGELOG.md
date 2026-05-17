# CHANGELOG

All notable changes to PlexMatch should be documented here.

## [Unreleased]

## [0.1.18] - 2026-05-17
- Align the browser auth URL with PlexAPI's current `https://app.plex.tv/auth/#!?...` format.
- Add the full Plex device context to the auth URL and request headers so the consent screen identifies `PlexMatch` instead of `0`.
- Add Plex nonce and scope claims to the signed device JWT used for PIN exchange.
- Expire stored PIN sessions created by older auth URL formats so users receive a fresh link.
- Bump project/package version to `0.1.18`.

## [0.1.17] - 2026-05-17
- Fix Plex PIN auth exchange by storing the generated JWK `kid` and including it in the signed device JWT header.
- Replace expired or old-format PIN sessions with a new auth URL instead of surfacing raw 404 tracebacks.
- Sanitize PIN auth HTTP failures so signed device JWTs are not exposed in CLI tracebacks.
- Add regression tests for JWT `kid` signing and sanitized expired-session handling.
- Bump project/package version to `0.1.17`.

## [0.1.16] - 2026-05-17
- Fix Plex PIN authentication link routing by restoring hash-based `https://app.plex.tv/auth#!?...` URL format so browser sign-in no longer stalls on a static Plex logo screen.
- Update auth URL regression test to validate the hash-route format.
- Bump project/package version to `0.1.16`.

## [0.1.15] - 2026-05-17
- Fix PIN auth URL construction to pass explicit Plex app context fields during sign-in.

## [0.1.14] - 2026-05-17
- Fix PIN auth messaging so the `https://plex.tv/link` fallback is shown only when Plex returns a valid 4-digit code.
- Prevent invalid long codes from being presented as manual link codes.
- Bump project/package version to `0.1.14`.

## [0.1.13] - 2026-05-17
- Improve PIN auth fallback UX: print a manual `https://plex.tv/link` path with the PIN code when `app.plex.tv/auth` fails.
- Include the same manual fallback URL/code in pending-approval messages.
- Bump project/package version to `0.1.13`.

## [0.1.12] - 2026-05-17
- Improve PIN auth flow UX: add `--auth-wait` to poll for browser approval, and include the auth URL in pending-approval messages.
- Bump project/package version to `0.1.12`.

## [0.1.9] - 2026-05-17
- Document Plex JWT authentication expectations for users: PIN/JWK registration paths, nonce-based refresh flow, and 7-day token rotation guidance.
- Bump project/package version to `0.1.9`.

## [0.1.8] - 2026-05-17
- Align Plex integration flow closer to watchlistarr: use `allFriendsV2` GraphQL for friend discovery, discover watchlist pagination for self watchlist, and paged friend watchlist GraphQL query.
- Add common Plex request headers including `User-Agent`, and bump client/version metadata to `0.1.8`.

## [0.1.7] - 2026-05-17
- Improve `test_api.py` to validate real GraphQL connectivity by sending a `users` query with Plex client headers and both auth header variants (`X-Plex-Token` and `Authorization: Bearer`).
- Align client version header and package metadata to `0.1.7`.

## [0.1.6] - 2026-05-17
- Add `test_api.py`, a standalone Plex API connectivity test script with CLI arguments, helpful status output, and clearer error diagnostics.

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
