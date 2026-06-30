---
name: cleanup-issue
description: Return an active GoShipit issue to todo or archive it.
---

# Cleanup Issue

## When To Use

Use when the user decides the active issue should leave execution.

## Required Inputs

- Active issue id
- Destination: `todo` or `archive`
- Human-readable note
- Whether to remove the managed worktree. This is required for `todo`.

## Allowed State Reads

- Active issue file
- Run file and journal

## Allowed State Writes

- Move issue from `execution` to `todo` or `archive`
- Append cleanup note to `state/runs/<issue-id>/journal.md`
- Append cleanup fields to `state/runs/<issue-id>/run.yaml`

## Allowed Target Repo Writes

Only removing a known GoShipit-managed worktree when requested.

## Scripts Or Commands

Run:

```sh
go-ship-it cleanup-issue <issue-id> --destination todo --note <note> --remove-worktree
go-ship-it cleanup-issue <issue-id> --destination archive --note <note>
```

## Human Approval Gates

Ask before removing a worktree. Returning to `todo` requires removal so the next start is clean.

## Evidence To Write

Cleanup note and final issue location.

## Next Recommended Skill

None.

## Failure Behavior

Do not remove files unless the active issue and managed worktree path are verified.
