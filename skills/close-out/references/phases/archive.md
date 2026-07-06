# Phase: archived

Close the issue out for good.

## Inputs

- A published PR (`pull_request.published_url` recorded), or — for repos with `pull_request.provider: none` — a signed-off local `pr.md` with no publish step required.

## Outputs

- The issue moved out of execution into the archive folder, with phase `archived`.

```sh
go-ship-it cleanup-issue <repo>/<issue-id> --destination archive --confirm --note "<final note>" --remove-worktree
go-ship-it export-run <repo>/<issue-id>
```

Archive first, then `export-run`. `export-run` works on an archived issue, and running it after cleanup records a fresh snapshot that reflects the closed state; exporting before cleanup would leave a stale `run.export_stale` warning on the archived run.

## Evidence

- Cleanup metadata on the run: `cleanup_destination` and `closed_at`.
- A fresh `export-run` evidence snapshot taken after archiving, so it reflects the closed state.

## Gate

- HUMAN. Archive is **terminal**: there is no reopen or unarchive. `cleanup-issue --destination archive` requires `--confirm` to acknowledge this before it will proceed. Ask the user before archiving, and never bundle archive with publish in a single step. If the worktree has uncommitted changes, cleanup refuses to remove it — commit first, or archive without `--remove-worktree` to preserve the worktree for inspection.
