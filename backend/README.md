# backend

FastAPI app, `uv`-managed. See the repo root [README.md](../README.md) for
the full local-setup instructions and [../wiki/runbook.md](../wiki/runbook.md)
for running this directly on the host (outside Docker) and troubleshooting.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
uv run pytest
```

Layout, models, and conventions: [../wiki/architecture.md](../wiki/architecture.md)
and [../wiki/data-model.md](../wiki/data-model.md).
