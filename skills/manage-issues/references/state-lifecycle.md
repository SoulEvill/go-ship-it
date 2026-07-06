# State Lifecycle

GoShipit keeps coarse issue state in folders:

```text
todo -> execution -> archive
```

Only `start-issue` moves `todo` to `execution`. `cleanup-issue` moves `execution` back to `todo` (the return path this skill owns) or forward to `archive` — but `archive` is the `close-out` skill's terminal gate (see `## Archiving`), not a routine manage-issues cleanup.

## Duplicate Starts

If an issue is already active, starting it again should return the existing run details rather than creating a second worktree. Treat that as an active-run handoff, not a new run.

## Claim Identity

Each active run has:

- `claimed_by`: a human-readable actor label, either supplied with `--claimed-by` or derived locally.
- `claim_id`: a deterministic id for the issue/run/worktree combination.
- `.go-ship-it/context.yaml`: a worktree-local context file ignored by Git.

Use issue id plus claim id to keep parallel sessions from mixing runs.

## Returning To Todo

Returning an issue to `todo` is a human decision, and it is the ONLY execution-state move this skill owns. Remove the managed worktree when returning to todo so the next start creates a clean branch and worktree.

## Archiving

Archiving is close-out gate 3: the LAST close-out gate, and it is terminal — there is no `reopen` or `unarchive`. It is not a routine manage-issues cleanup decided purely by user acceptance. Reach it only after the `close-out` skill's full flow has completed:

```text
verify-run <repo>/<issue-id> --strict is clean
  -> prepare-pr
  -> user reviews pr.md (and evidence.md)
  -> publish-pr --approved            # provider: none repos skip publish; the signed-off local pr.md is the gate
  -> cleanup-issue <repo>/<issue-id> --destination archive --confirm --note <note>
```

Archiving requires `--confirm` because it is irreversible; record a human-readable cleanup note. `manage-issues` owns only the `execution -> todo` return path for unfinished work — archiving a finished issue belongs to the `close-out` skill, which enforces the verify/prepare/publish gates above. Do not cross the terminal archive gate from a cleanup mindset without going through `close-out`.

## Manual Repair

Manual file moves are repair work only. Run `go-ship-it doctor`, explain the finding, and make the smallest state correction needed.
