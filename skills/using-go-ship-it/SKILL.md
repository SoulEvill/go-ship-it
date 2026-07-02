---
name: using-go-ship-it
description: Use at the start of a GoShipit session to orient to the control repo, lifecycle skills, CLI state, and target worktree boundaries.
---

# Using GoShipit

## When To Use

Use when starting a session in the GoShipit control repo, when the user asks to work on a GoShipit issue, or when the session needs orientation before using lifecycle skills.

## Core Model

GoShipit is a local-first control workspace for agent-assisted software work.

The GoShipit package owns skills, hooks, references, diagnostics, and the CLI. A GoShipit control root owns lifecycle state, run evidence, and managed worktrees. In clone-based development these may be the same directory. In package-install mode they are usually different directories.

Use this to find the installed package root when an agent needs the bundled skills and hooks:

```sh
go-ship-it package-root
```

## First Commands

Before changing state, run these from the GoShipit control repo root:

```sh
go-ship-it status
go-ship-it doctor
```

Use `status` for orientation and `doctor` for consistency checks.

## Working Directory Guard

Before any lifecycle work, prove which repository you are in:

```sh
pwd
git rev-parse --show-toplevel
```

The control root is the workspace where GoShipit state lives. It should contain:

```text
state/
worktrees/
```

In clone-based development the control root may also contain `pyproject.toml`, `skills/`, and plugin manifests. In package-install mode those live under `go-ship-it package-root` instead.

If the session starts somewhere else, either change to the control root or pass it explicitly:

```sh
go-ship-it --root <control-root> status
go-ship-it --root <control-root> doctor
```

Do not continue lifecycle work from a target repo checkout or target issue worktree. Target repo code changes happen inside the active issue worktree only after `go-ship-it show-run <issue-id>` confirms the worktree path.

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
