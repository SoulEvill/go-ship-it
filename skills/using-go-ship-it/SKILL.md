---
name: using-go-ship-it
description: Use when starting a GoShipit session, finding the control root, choosing the right GoShipit skill, or checking package and worktree boundaries.
---

# Using GoShipit

## When To Use

Use when starting a session in the GoShipit control repo, when the user asks to work on a GoShipit issue, or when the session needs orientation before using lifecycle skills.

Treat natural phrases like "use GoShipit", "Go Ship It this project", "go ship it this project", "start with GoShipit", or "let's use GoShipit here" as requests to start with this skill.

## Core Model

GoShipit is a local-first control workspace for agent-assisted software work.

The GoShipit package owns skills, hooks, references, diagnostics, and the CLI. A GoShipit control root owns lifecycle state, run evidence, and managed worktrees. In clone-based development these may be the same directory. In package-install mode they are usually different directories.

Use this to find the installed package root when an agent needs the bundled skills and hooks:

```sh
go-ship-it package-root
```

For the package, CLI, and maintainer surfaces, read `references/command-surface.md`.

## Orientation

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

Registered target repos live under visible repo folders:

```text
state/repos/<repo>/
  repo.yaml
  context.md
```

Read `state/repos/<repo>/context.md` for repo-level background before working an issue in that repo. Add concise repo-wide gotchas there only when the learning should apply across future issues.

In clone-based development the control root may also contain `pyproject.toml`, `skills/`, and plugin manifests. In package-install mode those live under `go-ship-it package-root` instead.

If the session starts somewhere else, either change to the control root or pass it explicitly:

```sh
go-ship-it --root <control-root> status
go-ship-it --root <control-root> doctor
```

Do not continue lifecycle work from an arbitrary target repo checkout. Target repo code changes happen inside the active issue worktree only after `go-ship-it show-run <issue-id>` confirms the worktree path.

Inside a managed issue worktree, `.go-ship-it/context.yaml` locks the session to the issue/run. Run-bound commands can omit the issue id there; use `--current` when you want the command to be explicit:

```sh
go-ship-it status
go-ship-it show-run
go-ship-it show-run --current
go-ship-it run-check --current --check test
go-ship-it handoff --write
```

If current-run detection fails or resolves a different issue than expected, stop and ask the user to confirm the intended issue before writing evidence.

## State Rules

State changes should go through the GoShipit CLI.

Do not move issue files manually unless the user explicitly asks for repair work and `doctor` output shows why repair is needed.

Do not edit target repositories from the control repo checkout. Target edits belong inside the active issue worktree.

## Skill Routing

Keep the agent-facing skill surface small:

- `manage-issues` when initializing a control root, registering a repo, creating a todo, starting work, checking status, or cleaning up an active issue.
- `work-issue` when investigating, proposing, implementing, testing, reviewing, or recording run evidence inside an active issue.

## Product Boundary

GoShipit does not automatically launch headless agents, discover work, create PRs, or integrate with GitHub or Jira in the local-first package path.

Remote integrations are optional future extensions. Keep local lifecycle evidence useful without them.

## Handoff Habit

When preparing a handoff, include:

- issue id
- target repo id
- active branch and worktree
- claim id and claimed-by label
- current phase
- important evidence paths
- commands run and results
- remaining warnings from `doctor` or `verify-run`

For an explicit handoff file, run:

```sh
go-ship-it handoff <issue-id> --write
# or, inside the managed worktree:
go-ship-it handoff --current --write
```
