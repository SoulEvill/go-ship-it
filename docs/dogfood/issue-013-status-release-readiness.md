# Status And Release Readiness Dogfood

Date: 2026-07-02

## Problem

The top-level CLI had too many flat commands for a first impression. The system worked, but users had to infer the normal path from terse help and docs.

Release checks also existed as separate commands, which made it easy to forget one before handing the repo to a user.

## Changes

- Added a normal-path summary to `go-ship-it --help`.
- Added first-run guidance. This was later simplified so `go-ship-it init` only creates the control root and `go-ship-it register-repo` handles repo onboarding.
- Made `go-ship-it status` more like a command center: control root, package root, branch, active issue phase, worktree, and useful next commands.
- Added `scripts/release-check.py` as the script-first release gate.
- Added `Justfile` as a lightweight convenience wrapper for common dev/release commands.

## User Model

Use the small normal path first:

```sh
go-ship-it init
go-ship-it register-repo my-repo /path/to/repo --test-command "uv run pytest"
go-ship-it add-issue --repo my-repo --title "Fix parser" --problem "Parser drops quoted values."
go-ship-it start-issue my-repo/issue-001
go-ship-it status
go-ship-it run-check my-repo/issue-001 --check test
go-ship-it cleanup-issue my-repo/issue-001 --destination archive --note "Done."
```

Use `status` to orient. Use detailed commands like `show-run`, `append-note`, `append-log`, `verify-run`, and `export-run` when needed.

## Release Gate

```sh
scripts/release-check.py
```

Optional:

```sh
just release-check
```

`just` is a convenience wrapper only. The script remains the reliable path.
