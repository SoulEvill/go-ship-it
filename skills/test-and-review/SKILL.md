---
name: test-and-review
description: Run configured checks and review evidence for an active GoShipit issue.
---

# Test And Review

## When To Use

Use after implementation and before cleanup.

## Required Inputs

- Active issue id
- Worktree path
- Repo registry commands

## Allowed State Reads

- Active issue file
- Run file and journal
- Target repo files inside the issue worktree

## Allowed State Writes

- Set phase to `test`
- Record configured command evidence through GoShipit
- Append review evidence to `state/runs/<issue-id>/journal.md` through GoShipit

## Allowed Target Repo Writes

Only source or test fixes inside the active issue worktree, when the user asks to address review findings.

## Scripts Or Commands

Use the local template at `references/test-review-template.md`.

```sh
go-ship-it set-phase <issue-id> test --note "<ready for checks>"
go-ship-it run-check <issue-id> --check setup
go-ship-it run-check <issue-id> --check test
go-ship-it run-check <issue-id> --check lint
go-ship-it append-note <issue-id> --section "Review" --phase test --note "<review findings and readiness>"
```

Run configured setup, test, and lint commands from `state/repos/<repo>.yaml` when present. Skip absent optional commands only after recording why in the review note.

## Human Approval Gates

Ask before skipping a failing check or accepting a review finding as intentional.

## Evidence To Write

Commands run, results, failures, review findings, and final readiness summary.

Phase completion evidence is command YAML under `state/runs/<issue-id>/commands/` plus a review note recorded with `go-ship-it append-note`.

## Next Recommended Skill

`cleanup-issue`

## Failure Behavior

Leave the issue in execution and report the failing evidence.
