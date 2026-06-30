#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

exec "$ROOT/scripts/run-target-e2e.py" \
  --target-id parawave \
  --target-path "$ROOT/../parawave" \
  --setup-command "env -u VIRTUAL_ENV uv sync --extra dev" \
  --test-command "env -u VIRTUAL_ENV uv run --extra dev pytest -q" \
  "$@"
