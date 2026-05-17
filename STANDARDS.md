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
- Provide useful error messages for invalid tokens, inaccessible users, empty watchlists, and no overlaps.

## Testing Standards
- Use deterministic unit tests with stable fixtures.
- Mock Plex API calls in unit tests.
- Keep live API calls out of default test runs.
- Add regression tests for normalization and duplicate handling.
- Separate integration tests from unit tests.

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
