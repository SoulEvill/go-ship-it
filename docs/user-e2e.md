# User E2E Checklist

Run this before trying GitHub, PR, or Jira integrations.

## Preflight

```sh
go-ship-it doctor
go-ship-it status
```

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

1. Register or inspect the target repo with `go-ship-it show-repo <repo>`.
2. Add an issue with `go-ship-it add-issue`.
3. Start it with `go-ship-it start-issue <issue-id>`.
4. Inspect it with `go-ship-it show-issue <issue-id>`.
5. Inspect the run with `go-ship-it show-run <issue-id>`.
6. Record investigation evidence with `set-phase` and `append-note`.
7. Record proposal evidence before implementation.
8. Implement only inside the worktree shown by `show-issue`.
9. Run configured checks with `go-ship-it run-check`.
10. Export evidence with `go-ship-it export-run`.
11. Cleanup to `archive` or return to `todo`.
12. Run `go-ship-it doctor` again.
