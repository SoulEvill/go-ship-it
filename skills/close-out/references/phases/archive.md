# Phase: archived

Close the issue out for good.

## Inputs

- A published PR (`pull_request.published_url` recorded), or — for repos with `pull_request.provider: none` — a signed-off local `pr.md` with no publish step required.

## Outputs

- The issue moved out of execution into the archive folder, with phase `archived`.

```sh
go-ship-it export-run <repo>/<issue-id>
go-ship-it cleanup-issue <repo>/<issue-id> --destination archive --confirm --note "<final note>" --remove-worktree
```

## Evidence

- Cleanup metadata on the run: `cleanup_destination` and `closed_at`.
- A fresh `export-run` evidence snapshot taken before archiving.

## Gate

- HUMAN. Archive is **terminal**: there is no reopen or unarchive. `cleanup-issue --destination archive` requires `--confirm` to acknowledge this before it will proceed. Ask the user before archiving, and never bundle archive with publish in a single step. If the worktree has uncommitted changes, cleanup refuses to remove it — commit first, or archive without `--remove-worktree` to preserve the worktree for inspection.
