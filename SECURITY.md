# SECURITY

## Security Scope and Ownership
This policy covers local development, CLI execution, Plex token handling, logs, generated output, and future integrations.

The project maintainer owns security decisions until formal ownership is assigned.

## Credential Handling Policy
- Store Plex tokens only in approved local mechanisms such as environment variables or `.env` files.
- Never commit `.env` files or credentials.
- Provide `.env.example` with placeholder values only.
- Never print tokens in normal output, debug output, logs, exceptions, screenshots, or test fixtures.
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
- V1 is local-only and should not expose a listening service.
- Future web or hosted modes must receive a separate security review.
- Keep dev/test credentials separate from any real user tokens where practical.
- Avoid persistent storage of user watchlists in V1.
- If caching is added, document retention and deletion behavior.

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
