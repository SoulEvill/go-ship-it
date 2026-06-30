---
name: propose-fix
description: Write a concise proposal for an active GoShipit issue before implementation.
---

# Propose Fix

## When To Use

Use after investigation and before editing target source files.

## Required Inputs

- Active issue id
- Investigation notes

## Allowed State Reads

- Active issue file
- Run journal
- Target repo files inside the issue worktree

## Allowed State Writes

- Append proposal notes to `state/runs/<issue-id>/journal.md`

## Allowed Target Repo Writes

None.

## Scripts Or Commands

No required command in v0.

## Human Approval Gates

Ask for approval before implementation when the change affects behavior, public APIs, data formats, or release workflow.

## Evidence To Write

Recommended approach, alternatives considered, risks, and acceptance checks.

## Next Recommended Skill

`implement-fix`

## Failure Behavior

Leave the issue in execution and ask the user for the missing decision.
