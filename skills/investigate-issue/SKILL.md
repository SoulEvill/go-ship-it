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

- Append investigation notes to `state/runs/<issue-id>/journal.md`

## Allowed Target Repo Writes

None.

## Scripts Or Commands

No required command in v0. Use normal read-only repo inspection commands from the issue worktree.

## Human Approval Gates

Ask when the problem statement or acceptance criteria are ambiguous.

## Evidence To Write

Relevant files, observed behavior, reproduction notes, constraints, and open questions.

## Next Recommended Skill

`propose-fix`

## Failure Behavior

Leave the issue in execution and report what context is missing.
