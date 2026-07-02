---
name: using-go-ship-it
description: Use at the start of a GoShipit session to orient to the control repo, lifecycle skills, CLI state, and target worktree boundaries.
---

# Using GoShipit

## When To Use

Use when starting a session in the GoShipit control repo, when the user asks to work on a GoShipit issue, or when the session needs orientation before using lifecycle skills.

## Core Model

GoShipit is a local-first control repo for agent-assisted software work.

The GoShipit repo owns lifecycle state, skills, references, diagnostics, and evidence. Target repository edits happen in issue worktrees created by GoShipit.

## First Commands

Run these before changing state:

```sh
go-ship-it status
go-ship-it doctor
```

Use `status` for orientation and `doctor` for consistency checks.

## State Rules

State changes should go through the GoShipit CLI.

Do not move issue files manually unless the user explicitly asks for repair work and `doctor` output shows why repair is needed.

Do not edit target repositories from the control repo checkout. Target edits belong inside the active issue worktree.

## Skill Routing

Read the lifecycle skill that matches the current user intent:

- `add-issue` when creating a new todo issue.
- `start-issue` when claiming a todo and creating a worktree.
- `investigate-issue` when collecting context and writing findings.
- `propose-fix` when preparing a plan for approval.
- `implement-fix` when changing target repo code.
- `test-and-review` when validating and comparing evidence to acceptance criteria.
- `cleanup-issue` when returning an issue to todo or archiving it.

## Product Boundary

GoShipit does not automatically launch headless agents, discover work, create PRs, or integrate with GitHub or Jira in the local-first package path.

Remote integrations are optional future extensions. Keep local lifecycle evidence useful without them.

## Handoff Habit

When preparing a handoff, include:

- issue id
- target repo id
- active branch and worktree
- current phase
- important evidence paths
- commands run and results
- remaining warnings from `doctor` or `verify-run`
