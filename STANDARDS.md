# STANDARDS

## Coding Standards
- Python 3.11+.
- 4-space indentation.
- Type hints on public APIs.
- Use `snake_case` for modules/functions, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Keep Plex-specific logic behind API interfaces.
- Keep GraphQL query assumptions centralized and documented.
- Prefer small, testable functions for normalization, matching, scoring, and output formatting.

## CLI Standards
- Use clear flags and predictable exit codes.
- Support `--help` for all commands/options.
- Support `.env` loading without requiring it.
- Do not echo secrets.
- Auth commands may print only the final Plex token intentionally requested by the user.
- Keep saved device auth credentials separate from temporary PIN session state.
- Provide useful error messages for invalid tokens, inaccessible users, empty watchlists, and no overlaps.

## Web UI Standards
- Bind local web UI to `127.0.0.1` by default.
- Keep web data access cache-only unless a future decision explicitly changes that.
- Show cache setup guidance instead of triggering Plex API calls from web handlers.
- Keep controls ergonomic for repeated movie-night use: ranked users, filters, and random pick actions should be immediately visible.
- Avoid full user reranking on simple UI interactions such as selecting a user or making a random pick.
- Show stale cache state clearly when data is expired but still available.

## Testing Standards
- Use deterministic unit tests with stable fixtures.
- Mock Plex API calls in unit tests.
- Test auth refresh paths without live Plex calls or real private keys in fixtures.
- Keep live API calls out of default test runs.
- Add regression tests for normalization and duplicate handling.
- Separate integration tests from unit tests.
- Test FastAPI endpoints with cached fixtures and no live Plex calls.

## Documentation Standards
- Keep `README.md` high-level.
- Put system behavior and assumptions in `CONTEXT.md`.
- Put component and data-flow details in `ARCHITECTURE.md`.
- Record major decisions in `DECISIONS.md`.
- Update `ROADMAP.md` when priorities or phases change.
- Update `CHANGELOG.md` for user-facing or implementation-facing changes.

## Review Standards
- PRs require summary, rationale, and verification evidence.
- Minimum verification: `ruff check .` and `pytest -q`.
- Include risk notes when Plex API assumptions change.
- Update docs when behavior, command syntax, security posture, or architecture changes.

## Operational Standards
- Use structured logging where practical.
- Default logging level should not expose sensitive data.
- Debug logs may include response shapes but must redact tokens and sensitive identifiers where possible.
- Provide a clear bug report template later if the project becomes public.
- Cache refresh jobs should update only expired entries by default and continue past individual refresh failures.
- Scheduler token recovery should be sanitized and should not write refreshed tokens into `.env`.
