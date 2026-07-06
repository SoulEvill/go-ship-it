#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARAWAVE_PATH="${PARAWAVE_PATH:-$ROOT/../parawave}"
FEEDBACK_REPO_PATH="${FEEDBACK_REPO_PATH:-$ROOT}"

if ! PARAWAVE_ROOT="$(git -C "$PARAWAVE_PATH" rev-parse --show-toplevel 2>/dev/null)"; then
  echo "Parawave repo not found or not git-backed: $PARAWAVE_PATH" >&2
  echo "Set PARAWAVE_PATH=/path/to/parawave and retry." >&2
  exit 1
fi

if ! FEEDBACK_REPO_ROOT="$(git -C "$FEEDBACK_REPO_PATH" rev-parse --show-toplevel 2>/dev/null)"; then
  echo "GoShipit feedback repo not found or not git-backed: $FEEDBACK_REPO_PATH" >&2
  echo "Set FEEDBACK_REPO_PATH=/path/to/go-ship-it and retry." >&2
  exit 1
fi

uv run go-ship-it --root "$ROOT" init

uv run go-ship-it --root "$ROOT" register-repo parawave "$PARAWAVE_ROOT" \
  --test-command "uv run --extra dev --extra sqlite pytest tests/ -v --tb=short" \
  "$@"

uv run go-ship-it --root "$ROOT" register-repo go-ship-it "$FEEDBACK_REPO_ROOT" \
  --feedback \
  --test-command "uv run pytest -q"
