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
setup -> investigate -> propose -> implement -> review -> prepare-pr -> publish -> archived
```

Each issue runs on a `track`: `standard` requires every phase; `quick` skips investigate/propose
and starts at implement (promote with `go-ship-it set-track <repo>/<issue-id> standard`).
Both tracks cross the same close-out gates: prepare-pr (local, reversible), publish
(human-approved; blocked while verify-run has findings), archive (terminal; requires --confirm).

## Readiness Checks

Use `go-ship-it status` for daily orientation and `go-ship-it doctor` before user e2e testing, cleanup, or handoff. `doctor` is read-only and reports inconsistent state, missing repos, stale locks, and skill packaging issues.

Use `go-ship-it verify-run <repo>/<issue-id> --strict` as the pre-cleanup readiness gate. It treats warnings as failures so missing acceptance criteria evidence, missing handoff context, failed command records, or incomplete notes do not get silently archived.

Agents can use structured output for lifecycle checks:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <repo>/<issue-id> --json
```

## Notes And Logs

Use `go-ship-it append-note` for authored investigation, proposal, implementation, and review notes.

GoShipit writes generated records under each issue's `logs/` folder. `logs/events.jsonl` is the chronological trace, and `logs/commands/` stores setup, test, and lint command records.

GoShipit product feedback should become a normal issue under the `go-ship-it` repo, linked back to the source repo/issue/run where it was observed.

Cleanup only changes state in two ways:

```text
execution -> todo
execution -> archive
```

`execution -> todo` returns unfinished work (`manage-issues`). `execution -> archive` is terminal and
requires `--confirm`; it is normally reached only after the run has crossed the close-out gates
(prepare-pr, publish) for its track — see `go-ship-it verify-run <repo>/<issue-id> --strict`.
