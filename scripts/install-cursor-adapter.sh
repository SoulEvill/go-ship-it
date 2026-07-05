#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$ROOT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$TARGET/.cursor/rules"

cat > "$TARGET/.cursor/rules/go-ship-it.mdc" <<'EOF'
---
description: Use GoShipit local issue lifecycle, diagnostics, and skill references in this control repo.
alwaysApply: true
---

# GoShipit Cursor Rule

Use the GoShipit CLI for lifecycle state changes. Start orientation with:

```sh
go-ship-it status
go-ship-it doctor
```

If `go-ship-it` is not on PATH in a clone-based development checkout, retry with `uv run go-ship-it` from the control root.

Read `skills/using-go-ship-it/SKILL.md` first, then use `skills/manage-issues/SKILL.md` for issue state changes or `skills/work-issue/SKILL.md` for active-run work. Do not edit target repositories outside the active issue worktree.
EOF

cat > "$TARGET/AGENTS.md" <<'EOF'
# GoShipit Agent Instructions

This repository is a local-first control repo for issue lifecycle work.

Before acting, inspect `references/lifecycle.md` and `skills/using-go-ship-it/SKILL.md`.

Use `skills/manage-issues/SKILL.md` for initializing/registering repos, adding todos, starting issues, status checks, and cleanup.

Use `skills/work-issue/SKILL.md` for investigation, proposal, implementation, testing, review, and run evidence.

Use `go-ship-it status` for orientation and `go-ship-it doctor` before cleanup or user e2e handoff.

If `go-ship-it` is not on PATH in a clone-based development checkout, retry with `uv run go-ship-it` from the control root.

State changes should go through the GoShipit CLI. Target repo edits should happen only inside the active issue worktree.
EOF

echo "Installed GoShipit Cursor adapter to $TARGET"
