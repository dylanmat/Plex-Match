# SECURITY

## Security Scope and Ownership
This policy covers local development, CLI execution, Plex token handling, logs, generated output, and future integrations.

The project maintainer owns security decisions until formal ownership is assigned.

## Credential Handling Policy
- Store Plex tokens only in approved local mechanisms such as environment variables or `.env` files.
- Never commit `.env` files or credentials.
- Never commit `.plexmatch_pin_auth.json`, `.plexmatch_device_auth.json`, or other local auth artifacts.
- Docker deployments may place PIN/device auth artifacts under `.plexmatch/` through `PLEXMATCH_PIN_AUTH_PATH` and `PLEXMATCH_DEVICE_AUTH_PATH`; those files remain restricted credential material and must not be committed.
- Provide `.env.example` with placeholder values only.
- Never print tokens in normal output, debug output, logs, exceptions, screenshots, or test fixtures.
- The only print exception is `--auth-refresh`, which prints the final refreshed Plex token directly to the terminal for the user to copy into `.env`.
- `--auth-pin` may update `PLEX_TOKEN` in the project-local `.env` file after successful browser approval, but it must not print the token.
- Never print device private keys or signed device JWTs.
- Do not request or store Plex passwords.
- Prefer Plex tokens with the minimum practical access.
- Rotate tokens immediately after suspected exposure.

## Data Access and Classification Policy
- Public: project docs, code, and sample non-real fixtures.
- Internal: normalized metadata and watchlist comparison output.
- Sensitive: Plex tokens, account identifiers, user IDs, friend lists, watchlists, and viewing activity.
- Restricted: any credential, authentication artifact, or personally identifying account detail.

## AI Restrictions and Safety Boundaries
- Do not paste real Plex tokens into prompts or tickets.
- Do not include private user watchlists in public examples.
- Do not use AI tools to infer, guess, or reconstruct credentials.
- Human review is required before adding new external integrations that handle tokens or user watchlist data.

## Environment and Deployment Controls
- CLI operation is local-only.
- The V3 web UI binds to `127.0.0.1` by default and should only be exposed deliberately in Docker or trusted local networks.
- Docker Compose binds the web UI to `0.0.0.0` inside the container and publishes port `8000`; use this only on trusted local networks.
- Web reauthorization remains loopback-only. For Docker containers accessed through published ports or from another computer, use CLI auth commands rather than exposing browser-initiated reauthorization.
- Future hosted modes must receive a separate security review.
- Keep dev/test credentials separate from any real user tokens where practical.
- Avoid persistent storage of user watchlists in V1.
- The local SQLite cache stores normalized users, watchlists, and local library metadata only; it must not store Plex tokens, local server tokens, or token hashes.
- `.plexmatch/` is ignored by git, and `--clear-cache` deletes cached metadata.
- Cache retention defaults to 6 hours and can be changed with `PLEX_CACHE_TTL_HOURS` or `--cache-ttl-hours`.
- The web UI reads cache only for comparison data and must not expose `.env`, Plex tokens, or local server tokens.
- The web UI may initiate Plex PIN/JWK reauthorization from local loopback clients only when `PLEX_TOKEN` is an expired JWT. It may return short-lived Plex approval URLs and auth/cache status, but it must not return final Plex tokens, device private keys, signed device JWTs, or `.env` contents.
- The CLI scheduler may read Plex credentials to refresh cache entries; it must not expose tokens in cache, logs, or web responses.
- The CLI scheduler may use saved device credentials to recover from an expired Plex token, but it must not write refreshed tokens into `.env`.
- Successful `--auth-pin` may trigger CLI-owned cache refresh with the fresh in-memory token immediately after updating `.env`.
- Expired cache entries may remain visible as stale internal metadata until refreshed or cleared.
- `.plexmatch_device_auth.json` is restricted local credential material. If the matching Plex authorized device is deleted or this file is lost, run the PIN flow again.

## Dependency and Runtime Controls
- Pin or constrain dependencies once implementation stabilizes.
- Use dependency scanning where practical.
- Avoid packages that require unnecessary credential or browser access.

## Incident Reporting and Response
- Treat leaked Plex tokens as compromised.
- Remove exposed tokens from git history or issue trackers where possible.
- Rotate affected tokens immediately.
- Document security-impacting changes in `CHANGELOG.md` and `DECISIONS.md`.

## Compliance Notes
No formal regulatory scope is currently defined. Reassess if this becomes hosted, multi-user, monetized, or integrated with additional account providers.
