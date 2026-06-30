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

- Append test and review evidence to `state/runs/<issue-id>/journal.md`

## Allowed Target Repo Writes

Only source or test fixes inside the active issue worktree, when the user asks to address review findings.

## Scripts Or Commands

Run configured setup, test, and lint commands from `state/repos/<repo>.yaml` when present.

## Human Approval Gates

Ask before skipping a failing check or accepting a review finding as intentional.

## Evidence To Write

Commands run, results, failures, review findings, and final readiness summary.

## Next Recommended Skill

`cleanup-issue`

## Failure Behavior

Leave the issue in execution and report the failing evidence.
