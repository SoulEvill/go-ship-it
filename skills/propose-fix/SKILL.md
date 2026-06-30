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

## Orientation

Before proposing, run:

```sh
go-ship-it show-issue <issue-id>
go-ship-it show-run <issue-id>
```

Read the issue and journal before choosing an approach.

## Allowed State Reads

- Active issue file
- Run journal
- Target repo files inside the issue worktree

## Allowed State Writes

- Set phase to `propose`
- Append proposal notes to `state/runs/<issue-id>/journal.md` through GoShipit

## Allowed Target Repo Writes

None.

## Scripts Or Commands

Use the local template at `references/proposal-template.md`.

```sh
go-ship-it set-phase <issue-id> propose --note "<investigation summary>"
go-ship-it append-note <issue-id> --section "Proposal" --phase propose --note "<filled proposal>"
```

## Human Approval Gates

Ask for approval before implementation when the change affects behavior, public APIs, data formats, or release workflow.

## Evidence To Write

Recommended approach, alternatives considered, risks, and acceptance checks.

Phase completion evidence is a proposal journal section recorded with `go-ship-it append-note`.

## Next Recommended Skill

`implement-fix`

## Failure Behavior

Leave the issue in execution and ask the user for the missing decision.
