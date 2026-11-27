# FixIt Backend Agent Instructions

## Project purpose

Build the Python backend for the FixIt marketplace. One FastAPI application serves the Customer, Provider, and Admin frontends.

## Mandatory workflow

1. Read this file before making repository changes.
2. Read the relevant issue, product requirements, and API contract before implementing a feature.
3. Work on one approved phase or issue at a time.
4. Do not invent product behavior or silently resolve ambiguous requirements. Record questions and request a decision.
5. Do not replace working frontend contracts without an approved migration plan.
6. Add or update automated tests for every behavior change.
7. Run all required checks before declaring work complete.
8. Explain how to reproduce and test each phase.
9. Keep documentation and examples synchronized with implementation.
10. Never commit secrets, credentials, real user data, or local environment files.

## Architecture rules

- Use a modular monolith. Do not introduce microservices without explicit approval.
- Keep HTTP routes, schemas, business services, and persistence concerns separated.
- Use `/api/v1` for versioned application endpoints.
- Validate all untrusted input on the server.
- Enforce authentication, authorization, and resource ownership in the backend. Frontend visibility is not security.
- Add explicit database constraints and migrations when persistence is introduced.
- Store money as integer kobo, never floating-point naira.
- Do not add payment, messaging, storage, or other external integrations without approved requirements.

## Quality gates

Run before every PR:

```bash
ruff check .
ruff format --check .
pytest -q
```

When database code is introduced, tests must also exercise migrations against a test PostgreSQL database.

## Versioning

- Follow Semantic Versioning: MAJOR.MINOR.PATCH.
- The initial project foundation starts at `0.1.0`.
- Every merged PR that changes application code or project behavior must update the version consistently in `pyproject.toml` and the application version source/configuration, and update `CHANGELOG.md`.
- Documentation-only changes that do not affect behavior do not require a version bump.
- Use a patch increment for backward-compatible fixes, a minor increment for backward-compatible features, and a major increment for breaking changes. Before `1.0.0`, use `0.MINOR.PATCH` conventions.
- Do not bump versions for unmerged commits within the same PR. The version bump belongs in the PR being merged.

## Phase completion

A phase is complete only when its acceptance criteria are met, tests pass, documentation is updated, and the PR is reviewed. Never mark an issue complete merely because the server starts.
