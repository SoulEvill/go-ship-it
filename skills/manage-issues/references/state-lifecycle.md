# State Lifecycle

GoShipit keeps coarse issue state in folders:

```text
todo -> execution -> archive
```

Only `start-issue` moves `todo` to `execution`. Only `cleanup-issue` moves `execution` back to `todo` or forward to `archive`.

## Duplicate Starts

If an issue is already active, starting it again should return the existing run details rather than creating a second worktree. Treat that as an active-run handoff, not a new run.

## Claim Identity

Each active run has:

- `claimed_by`: a human-readable actor label, either supplied with `--claimed-by` or derived locally.
- `claim_id`: a deterministic id for the issue/run/worktree combination.
- `.go-ship-it/context.yaml`: a worktree-local context file ignored by Git.

Use issue id plus claim id to keep parallel sessions from mixing runs.

## Returning To Todo

Returning an issue to `todo` is a human decision. Remove the managed worktree when returning to todo so the next start creates a clean branch and worktree.

## Archiving

Archive when the user accepts the result, decides the work is no longer needed, or wants to preserve the run as closed. Record a human-readable cleanup note.

## Manual Repair

Manual file moves are repair work only. Run `go-ship-it doctor`, explain the finding, and make the smallest state correction needed.
