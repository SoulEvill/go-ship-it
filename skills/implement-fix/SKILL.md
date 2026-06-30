---
name: implement-fix
description: Implement an approved fix inside the active issue worktree.
---

# Implement Fix

## When To Use

Use after a proposal is approved or the user explicitly asks to implement a narrow change.

## Required Inputs

- Active issue id
- Worktree path
- Approved proposal or explicit user instruction

## Orientation

Before editing, run:

```sh
go-ship-it show-run <issue-id>
```

Confirm proposal approval and the active worktree path before modifying target repo files.

## Allowed State Reads

- Active issue file
- Run journal
- Target repo files inside the issue worktree

## Allowed State Writes

- Set phase to `implement`
- Append implementation notes to `state/runs/<issue-id>/journal.md` through GoShipit

## Allowed Target Repo Writes

Only files inside the active issue worktree.

## Scripts Or Commands

Use the local template at `references/implementation-notes-template.md`.

```sh
go-ship-it set-phase <issue-id> implement --note "<implementation started>"
go-ship-it append-note <issue-id> --section "Implementation" --phase implement --note "<filled implementation notes>"
```

## Human Approval Gates

Ask before changing scope beyond the proposal.

## Evidence To Write

Changed files and implementation notes.

Phase completion evidence is an implementation journal section recorded with `go-ship-it append-note`.

## Next Recommended Skill

`test-and-review`

## Failure Behavior

Leave the issue in execution and summarize the blocker.
