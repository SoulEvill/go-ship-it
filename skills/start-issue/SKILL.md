---
name: start-issue
description: Claim a GoShipit todo issue and create its isolated target repo worktree.
---

# Start Issue

## When To Use

Use when the user picks a todo issue and wants to begin work in an isolated worktree.

## Required Inputs

- Issue id
- Optional claimed-by label for the current human or agent thread

## Orientation

Before starting, run:

```sh
go-ship-it list-issues --state todo
go-ship-it show-issue <issue-id>
```

Confirm the issue is still in `todo` and the target repo is the expected repo.

## Allowed State Reads

- `state/issues/todo/<issue-id>.md`
- `state/repos/<repo>.yaml`
- `state/runs/<issue-id>/`

## Allowed State Writes

- Move the issue from `todo` to `execution`
- Create `state/runs/<issue-id>/`
- Create `state/runs/<issue-id>/claim.lock/`
- Create `state/runs/<issue-id>/run.yaml`

## Allowed Target Repo Writes

Only Git worktree and branch creation through `git worktree add`.

## Scripts Or Commands

Run:

```sh
go-ship-it start-issue <issue-id> --claimed-by <thread-label>
```

## Human Approval Gates

If the issue is already active, report the existing active run and ask whether the user wants to continue that run.

## Evidence To Write

The run file and updated issue frontmatter are the evidence.

## Next Recommended Skill

`investigate-issue`

## Failure Behavior

Do not move the issue out of `todo` if the target repo or worktree setup fails.
