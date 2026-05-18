# CHANGELOG

All notable changes to PlexMatch should be documented here.

## [Unreleased]
- Improve local web UI responsiveness by memoizing cache-backed rankings and comparisons until the SQLite cache changes.
- Avoid reranking all users when selecting a different user in the web UI.

## [0.3.0] - 2026-05-17
- Add local FastAPI web UI available with `--web`.
- Add cache-only comparison service for ranked `self` comparisons.
- Rank top matching users by total scored matches.
- Add web endpoints for status, ranked users, comparisons, and high/low confidence random picks.
- Document web cache prerequisites and local-only security model.

## [0.2.0] - 2026-05-17
- Add project-local SQLite cache at `.plexmatch/cache.sqlite3`.
- Cache normalized users, watchlists, and local Plex library items with a default 6-hour TTL.
- Add `--no-cache`, `--clear-cache`, and `--cache-ttl-hours`.
- Add `PLEXMATCH_CACHE_PATH` and `PLEX_CACHE_TTL_HOURS` configuration support.
- Keep cache namespaces token-free and exclude `.plexmatch/` from git.

## [0.1.32] - 2026-05-17
- Add optional local Plex server availability enrichment for configured local libraries.
- Add a +10 score bonus for candidates found on the local Plex server.
- Include local availability in table, plain-text, and JSON comparison output.
- Add regression coverage for local Plex XML parsing, availability matching, scoring, and output.
- Bump project/package version to `0.1.32`.

## [0.1.31] - 2026-05-17
- Normalize one-sided candidate scoring so `user_a` and `user_b` both start at base score 10.
- Keep support bonuses additive on top of the equal one-sided base score.
- Bump project/package version to `0.1.31`.

## [0.1.30] - 2026-05-17
- Tighten `--random high` to sample only from higher-scored results instead of weighting every result.
- Exclude base score `10` items from high-confidence random selection.
- Keep `--random low` as uniform selection across all results.
- Add regression coverage for the high-confidence selection pool.
- Bump project/package version to `0.1.30`.

## [0.1.29] - 2026-05-17
- Change `--random` to high-confidence score-weighted selection by default.
- Add explicit `--random high` and `--random low` modes.
- Use `--random low` for uniform random selection that ignores score.
- Add regression tests for weighted and uniform random selection behavior.
- Bump project/package version to `0.1.29`.

## [0.1.28] - 2026-05-17
- Add cross-user support scoring for comparison candidates.
- Add `+5` to an item's score for each other accessible Plex user whose watchlist contains that item.
- Include support counts in table, plain-text, and JSON output.
- Skip inaccessible secondary watchlists during support scoring so private friends do not block the main comparison.
- Add regression coverage for support matching and score bonuses.
- Bump project/package version to `0.1.28`.

## [0.1.27] - 2026-05-17
- Improve candidate matching by treating unique same-title entries as overlaps when one side lacks a year.
- Preserve title/year separation when both sides have known but different years.
- Try richer friend watchlist GraphQL fields (`year`, `originallyAvailableAt`, `guid`) before falling back to the minimal query.
- Add regression coverage for missing-year title fallback, known-year conflicts, and richer friend node parsing.
- Bump project/package version to `0.1.27`.

## [0.1.26] - 2026-05-17
- Change comparison output to list all filtered watchlist candidates from both users instead of only strict overlaps.
- Add source labels to match output: `both`, `user_a`, and `user_b`.
- Score strict overlaps highest while still scoring one-sided items for recommendation diagnostics.
- Add regression coverage for all-candidate matching and candidate scoring.
- Bump project/package version to `0.1.26`.

## [0.1.25] - 2026-05-17
- Merge Plex XML friend metadata with community `allFriendsV2` results.
- Prefer community GraphQL friend IDs for command-facing friend IDs because friend watchlist lookup depends on the community resolver.
- Keep Plex account IDs visible as metadata in `--list-users`.
- Add a Community ID column to user output.
- Add regression coverage for XML/community friend ID merging.
- Bump project/package version to `0.1.25`.

## [0.1.24] - 2026-05-17
- Use friend UUIDs from `https://plex.tv/api/users/` as command-facing IDs because friend watchlist GraphQL resolves `user(id:)` through the Plex user UUID.
- Preserve numeric Plex account IDs as separate `account_id` metadata in user output.
- Add an Account ID column to `--list-users`.
- Bump project/package version to `0.1.24`.

## [0.1.23] - 2026-05-17
- Use numeric Plex account IDs from `https://plex.tv/api/users/` for friend entries so friend watchlist GraphQL receives the expected identifier.
- Replace friend watchlist GraphQL `data: null` crashes with sanitized errors that include Plex's GraphQL message when available.
- Add regression coverage for friend watchlist `data: null` handling.
- Bump project/package version to `0.1.23`.

## [0.1.22] - 2026-05-17
- Reduce self-watchlist pagination from 300 to 10 items per request to avoid Plex provider `X-Plex-Container-Size` 400 responses.
- Add `includeAdvanced` and `includeMeta` request flags used by current Plex Web watchlist requests.
- Fall back from `discover.provider.plex.tv` to `metadata.provider.plex.tv` for self watchlist retrieval.
- Add regression tests for provider fallback and all-provider sanitized 400 handling.
- Bump project/package version to `0.1.22`.

## [0.1.21] - 2026-05-17
- Move Discover watchlist authentication from the query string to the `X-Plex-Token` header to avoid token disclosure in HTTP error URLs.
- Add PlexAPI-compatible `includeCollections` and `includeExternalMedia` flags to self watchlist requests.
- Replace raw Discover 400/401 tracebacks with sanitized CLI errors.
- Add regression coverage for sanitized Discover failures and header-based token use.
- Bump project/package version to `0.1.21`.

## [0.1.20] - 2026-05-17
- Include the authenticated Plex account as a synthetic `self` user in `--list-users`.
- Accept `self` and `me` aliases for comparison commands so the signed-in account can be used as `--user-a` or `--user-b`.
- Route the signed-in account watchlist through the Discover watchlist endpoint while friend watchlists continue to use friend-specific GraphQL.
- Add a role column to user output to distinguish `self` from friends.
- Add regression tests for self user listing and self watchlist routing.
- Bump project/package version to `0.1.20`.

## [0.1.19] - 2026-05-17
- Use Plex's `https://plex.tv/api/users/` XML endpoint as the primary source for `--list-users`.
- Keep community GraphQL as a watchlist-specific integration instead of requiring it for user listing.
- Replace raw Plex 401 tracebacks with sanitized guidance to refresh and use the current JWT.
- Update Plex client version headers to `0.1.18` for API calls.
- Add regression tests for XML user parsing and token rejection messages.
- Bump project/package version to `0.1.19`.

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
