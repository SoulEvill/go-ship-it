#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARAWAVE_PATH="${PARAWAVE_PATH:-$ROOT/../parawave}"

if ! PARAWAVE_ROOT="$(git -C "$PARAWAVE_PATH" rev-parse --show-toplevel 2>/dev/null)"; then
  echo "Parawave repo not found or not git-backed: $PARAWAVE_PATH" >&2
  echo "Set PARAWAVE_PATH=/path/to/parawave and retry." >&2
  exit 1
fi

exec "$ROOT/scripts/run-target-e2e.py" \
  --target-id parawave \
  --target-path "$PARAWAVE_ROOT" \
  --setup-command "env -u VIRTUAL_ENV uv sync --extra dev" \
  --test-command "env -u VIRTUAL_ENV uv run --extra dev pytest -q" \
  "$@"
