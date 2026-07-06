# Issue 016: Repo Context Folders and Current Run Resolution

## Why

Parallel GoShipit sessions need a deterministic way to know which issue/run they are writing evidence for. Repo-level context also needs an obvious home that is visible without opening a central registry file.

## Changes

- Repo registration now writes `state/repos/<repo>/repo.yaml`.
- Repo registration also creates `state/repos/<repo>/context.md` for repo-wide background, commands, gotchas, and durable learnings.
- Flat `state/repos/<repo>.yaml` files are intentionally unsupported; repo config must live under `state/repos/<repo>/repo.yaml`.
- Managed worktrees can now run issue-bound commands without repeating the issue id.
- `--current` remains available as an explicit form.
- Current-run detection reads `.go-ship-it/context.yaml`, then verifies issue id, worktree, and claim id against `state/runs/<issue-id>/run.yaml` before writing state.

## Example

```sh
go-ship-it status
go-ship-it show-run
go-ship-it show-run --current
go-ship-it append-note --current --section "Investigation" --for-phase investigate --note "Read parser tests."
go-ship-it set-phase --current test --note "Ready for configured checks."
go-ship-it run-check --current --check test
go-ship-it handoff --write
```

## Design Notes

The worktree context file is not the source of truth. It is a session pointer. The run metadata remains authoritative, which keeps copied or stale worktree context from silently writing to the wrong issue.

If no context file is found, or if the context does not match the run claim, the command stops and asks for explicit issue context instead of guessing.
