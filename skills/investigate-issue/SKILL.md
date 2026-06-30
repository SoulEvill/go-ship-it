---
name: investigate-issue
description: Gather context for an active GoShipit issue without editing target source files.
---

# Investigate Issue

## When To Use

Use after `start-issue` when the agent needs to understand the code, reproduce behavior, or collect constraints.

## Required Inputs

- Active issue id
- Worktree path

## Allowed State Reads

- Active issue file
- Run file and journal
- Target repo files inside the issue worktree

## Allowed State Writes

- Set phase to `investigate`
- Append investigation notes to `state/runs/<issue-id>/journal.md` through GoShipit

## Allowed Target Repo Writes

None.

## Scripts Or Commands

Use the local template at `references/investigation-template.md`.

```sh
go-ship-it set-phase <issue-id> investigate --note "<why investigation started or resumed>"
go-ship-it append-note <issue-id> --section "Investigation" --phase investigate --note "<filled investigation notes>"
```

Use normal read-only repo inspection commands from the issue worktree.

## Human Approval Gates

Ask when the problem statement or acceptance criteria are ambiguous.

## Evidence To Write

Relevant files, observed behavior, reproduction notes, constraints, and open questions.

Phase completion evidence is a readable `Investigation` journal section recorded with `go-ship-it append-note`.

## Next Recommended Skill

`propose-fix`

## Failure Behavior

Leave the issue in execution and report what context is missing.
