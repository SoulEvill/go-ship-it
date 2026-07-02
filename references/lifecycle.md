# GoShipit Lifecycle

GoShipit uses three broad issue folders:

```text
todo -> execution -> archive
```

`todo` means an issue is available to start.

`execution` means one active run owns the issue and has a dedicated worktree.

`archive` means the issue is closed and no longer part of active work.

Detailed progress is stored as issue metadata:

```text
setup -> investigate -> propose -> implement -> test -> cleanup
```

## Readiness Checks

Use `go-ship-it status` for daily orientation and `go-ship-it doctor` before user e2e testing, cleanup, or handoff. `doctor` is read-only and reports inconsistent state, missing repos, stale locks, and skill packaging issues.

## Run Logs

Use `go-ship-it append-log` for lightweight comments about what happened during the run, especially process observations that may become future learning.

Sources are optional opaque pointers such as `transcript:/path/to/session.jsonl`, `file:docs/dogfood/...`, `command:state/runs/...`, or `url:https://...`. V0 stores these pointers but does not dereference them.

Cleanup only changes state in two ways:

```text
execution -> todo
execution -> archive
```
