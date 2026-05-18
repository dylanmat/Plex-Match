# AI Agent Workflow Guide

## Purpose
`AGENTS.md` defines AI agents used in PlexMatch development workflows, their boundaries, and handoff rules.

## Required Project Docs
- `README.md`: high-level project description.
- `CONTEXT.md`: system context for developers and AI tools.
- `ARCHITECTURE.md`: system build and integration blueprint.
- `SECURITY.md`: security policy, credential handling, data access, AI restrictions.
- `STANDARDS.md`: coding and operational standards.
- `DECISIONS.md`: architectural decision record.
- `ROADMAP.md`: project development priorities, sequencing, and status.
- `CHANGELOG.md`: release history.

## Workflow Stages
- Context intake: read `README.md`, `CONTEXT.md`, and current `DECISIONS.md`.
- Design: update `ARCHITECTURE.md` and document tradeoffs.
- Implementation: apply changes under `src/`, `tests/`, `configs/`, and `scripts/`.
- Verification: run tests and record key evidence.
- Documentation and release: update affected docs and `CHANGELOG.md`.

## Agent Catalog

### Planner Agent
- Purpose: turn requests into decision-complete implementation plans.
- Inputs: user request, `CONTEXT.md`, `ARCHITECTURE.md`, `ROADMAP.md`.
- Outputs: ordered implementation plan with acceptance criteria.
- Allowed actions: analysis, repo inspection, non-mutating checks.
- Disallowed actions: editing files during planning-only tasks.
- Handoff to: Implementer Agent.

### Implementer Agent
- Purpose: implement approved plans and keep behavior/docs aligned.
- Inputs: approved plan, codebase state, standards and security policies.
- Outputs: code/doc changes, UI changes when applicable, test results summary, risk notes.
- Allowed actions: edit files, run build/test/lint commands.
- Disallowed actions: bypassing security policy, logging secrets, or undocumented behavior changes.
- Handoff to: Reviewer Agent.

### Reviewer Agent
- Purpose: detect defects, regressions, and policy violations.
- Inputs: diffs, test evidence, `STANDARDS.md`, `SECURITY.md`.
- Outputs: prioritized findings and required fixes.
- Allowed actions: static review, risk analysis, validation checks.
- Disallowed actions: approving unresolved critical findings.
- Handoff to: Implementer Agent or Docs Agent.

### Docs Agent
- Purpose: keep required root docs accurate after changes.
- Inputs: merged behavior/design/policy changes.
- Outputs: synchronized updates to affected markdown docs.
- Allowed actions: edit docs, improve cross-links, clarify ownership.
- Disallowed actions: changing product behavior in docs-only tasks.
- Handoff to: Release Agent.

### Web UI Agent
- Purpose: plan and review local UI workflows without expanding token exposure.
- Inputs: cache-backed service behavior, UX requirements, `SECURITY.md`, and `STANDARDS.md`.
- Outputs: local UI implementation notes, endpoint expectations, and cache-only validation risks.
- Allowed actions: inspect frontend/backend UI code, propose or implement local UI changes during implementation tasks.
- Disallowed actions: adding web handlers that read Plex tokens or call Plex APIs without an accepted decision.
- Handoff to: Reviewer Agent or Docs Agent.

### Release Agent
- Purpose: finalize release notes and version-facing updates.
- Inputs: merged changes, decisions, and test outcomes.
- Outputs: `CHANGELOG.md` updates and release summary.
- Allowed actions: compile release deltas and readiness notes.
- Disallowed actions: shipping without required validation evidence.
- Handoff to: none.

## Coordination Rules
- Do not skip handoffs when ownership changes between planning, implementation, review, docs, and release.
- Resolve conflicts using source-of-truth docs in this order: `SECURITY.md`, `STANDARDS.md`, `ARCHITECTURE.md`, `CONTEXT.md`, `README.md`.
- PowerShell is acceptable and preferred on Windows automation paths.

## Pull Request Policy for Agent Workflows
- Include summary, rationale, and verification evidence.
- Minimum verification: `ruff check .` and `pytest -q`.
- Update `AGENTS.md` when agent roles, allowed actions, disallowed actions, handoffs, UI ownership, or update triggers change.
