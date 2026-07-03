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

Use `go-ship-it verify-run <issue-id> --strict` as the pre-cleanup readiness gate. It treats warnings as failures so missing acceptance criteria evidence, missing handoff context, failed command records, or incomplete journal evidence do not get silently archived.

Agents can use structured output for lifecycle checks:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <issue-id> --json
```

## Run Logs

Use `go-ship-it append-log` for lightweight comments about what happened during the run, especially process observations that may become future learning.

Sources are optional opaque pointers such as `transcript:/path/to/session.jsonl`, `file:docs/dogfood/...`, `command:state/runs/...`, or `url:https://...`. V0 stores these pointers but does not dereference them.

Cleanup only changes state in two ways:

```text
execution -> todo
execution -> archive
```
