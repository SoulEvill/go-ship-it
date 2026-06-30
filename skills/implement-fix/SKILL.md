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

## Allowed State Reads

- Active issue file
- Run journal
- Target repo files inside the issue worktree

## Allowed State Writes

- Append implementation notes to `state/runs/<issue-id>/journal.md`

## Allowed Target Repo Writes

Only files inside the active issue worktree.

## Scripts Or Commands

No required command in v0.

## Human Approval Gates

Ask before changing scope beyond the proposal.

## Evidence To Write

Changed files and implementation notes.

## Next Recommended Skill

`test-and-review`

## Failure Behavior

Leave the issue in execution and summarize the blocker.
