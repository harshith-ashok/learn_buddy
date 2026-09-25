# ADR 0001: Add ruff as a backend dev dependency in Phase 0

## Problem

`CLAUDE.md` mandates `ruff format` + `ruff check` for all Python code and
the Phase 0 `Makefile` needs a working `lint` target, but the backend
`pyproject.toml` had no dev dependencies at all yet.

## Options considered

1. Leave `make lint` referencing `ruff` and let it fail until Phase 1.
2. Add `ruff` as a dev dependency now, in Phase 0.

## Choice

Added `ruff` via `uv add --dev ruff`. It's a single, low-risk dependency
with no runtime footprint (never ships in the `backend/Dockerfile` runtime
stage — that stage only installs non-dev deps via `uv sync --frozen
--no-dev`), and it makes `make lint` actually do something from the first
commit instead of being a broken promise.

## Consequences

- `backend/pyproject.toml` and `backend/uv.lock` now carry a `ruff` entry
  under `[dependency-groups].dev` (or equivalent uv dev-group).
- No `ruff.toml` / `[tool.ruff]` config was added yet — default rules only,
  until Phase 1 decides on project-specific lint rules alongside the real
  `src/` layout.
