#!/usr/bin/env bash
# Commits a fresh working tree folder-by-folder, backdated one day apart.
# Review, then run: ./scripts/commit-phases.sh

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if git rev-parse HEAD >/dev/null 2>&1; then
  echo "error: repo already has commits — this expects a fresh 'git init' with nothing committed yet" >&2
  exit 1
fi

commit_phase() {
  local date="$1"
  local message="$2"
  shift 2
  git add -- "$@"
  GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit -m "$message"
}

commit_phase "2026-09-22T13:20:00+05:30" \
  "(chore): project scaffolding and config" \
  .env.example .github .python-version Makefile README.md \
  docker-compose.yml docker-compose.override.yml docker-compose.prod.yml \
  scripts

commit_phase "2026-09-23T13:20:00+05:30" \
  "(feat): backend" \
  backend

commit_phase "2026-09-24T13:20:00+05:30" \
  "(feat): frontend" \
  frontend

commit_phase "2026-09-25T13:20:00+05:30" \
  "(docs): wiki" \
  wiki

echo
echo "Done. Remaining uncommitted files:"
git status --short
