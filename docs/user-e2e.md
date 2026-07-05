# User E2E Checklist

Run this before trying GitHub, PR, or Jira integrations.

## Preflight

```sh
go-ship-it doctor
go-ship-it status
```

For a first-time control root, initialize state and register the first target repo together:

```sh
go-ship-it init \
  --repo-id my-repo \
  --repo-path /path/to/my-repo \
  --test-command "uv run pytest"
```

This creates the repo folder:

```text
state/repos/my-repo/
  repo.yaml
  context.md
  issues/
    todo/
    execution/
    archive/
```

Put durable repo-wide notes in `context.md`: setup gotchas, common commands, confusing conventions, and lessons that should apply across future issues.

## What Gets Created

During the first issue, GoShipit should create only local, inspectable artifacts:

```text
state/repos/<repo>/issues/todo/<issue-id>/issue.md
state/repos/<repo>/issues/execution/<issue-id>/issue.md
state/repos/<repo>/issues/execution/<issue-id>/run.yaml
state/repos/<repo>/issues/execution/<issue-id>/notes.md
state/repos/<repo>/issues/execution/<issue-id>/handoff.md
state/repos/<repo>/issues/execution/<issue-id>/logs/events.jsonl
state/repos/<repo>/issues/execution/<issue-id>/logs/commands/*.yaml
worktrees/<repo>/<issue-id>/.go-ship-it/context.yaml
```

`state/repos/<repo>/issues/execution/<issue-id>/run.yaml` is the active run metadata source of truth. `.go-ship-it/context.yaml` is only a worktree pointer back to that run and must match before current-run commands write notes or command records.

## Disposable Target Harness

For a repeatable local smoke test against any Git repo, use the generic target harness with explicit target values:

```bash
scripts/run-target-e2e.py \
  --target-id my-repo \
  --target-path /path/to/my-repo \
  --setup-command "uv sync" \
  --test-command "uv run pytest"
```

The harness clones the target into a temporary run root, registers that clone with isolated GoShipit state, drives the issue lifecycle through the CLI, and writes a Markdown report. It does not choose a default target repo.

### Contributor Fixture: Parawave

GoShipit contributors can use `scripts/dev/run-parawave-e2e.sh` inside this development workspace. Parawave is a local fixture for dogfooding; it is not a default target for users.

## Issue Flow

Use `skills/manage-issues/SKILL.md` for steps 1-3 and 11-12. Use `skills/work-issue/SKILL.md` for steps 4-10.

1. Initialize and register the target repo with `go-ship-it init --repo-id <repo> --repo-path <path>`, or inspect an existing target with `go-ship-it show-repo <repo>`.
2. Add an issue with `go-ship-it add-issue`.
3. Start it with `go-ship-it start-issue <repo>/<issue-id>`.
4. Inspect it with `go-ship-it show-issue <repo>/<issue-id>`.
5. Inspect the run with `go-ship-it show-run <repo>/<issue-id>`.
6. Confirm the worktree `.go-ship-it/context.yaml` matches the issue id and claim id.
7. From inside the managed worktree, use current-run detection for run-bound commands, for example `go-ship-it show-run` or the explicit `go-ship-it show-run --current`.
8. Record investigation evidence with `set-phase` and `append-note`.
9. Record proposal evidence before implementation.
10. Implement only inside the worktree shown by `show-issue`.
11. Run configured checks with `go-ship-it run-check --current --check test` from the worktree, or `go-ship-it run-check <repo>/<issue-id> --check test` from the control root.
12. Create an explicit resume snapshot with `go-ship-it handoff --write` from the worktree, or `go-ship-it handoff <repo>/<issue-id> --write` from the control root, when another session should continue.
13. Export evidence with `go-ship-it export-run`.
14. Run `go-ship-it verify-run <repo>/<issue-id> --strict` and resolve or explicitly report every warning before cleanup.
15. Cleanup to `archive` with `--remove-worktree` for completed work, or return to `todo` with `--remove-worktree` when work should be retried later.
16. Run `go-ship-it doctor` again.

For agent-driven checks, prefer structured output:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <repo>/<issue-id> --json
```
