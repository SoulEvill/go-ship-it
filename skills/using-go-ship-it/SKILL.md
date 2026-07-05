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

## Command Resolution

Resolve the GoShipit command before running lifecycle commands:

- If `go-ship-it` is on PATH, use `go-ship-it`.
- If this is a clone-based development checkout and `pyproject.toml` is present, use `uv run go-ship-it`.
- If a local virtualenv exists, `.venv/bin/go-ship-it` is also acceptable.

If bare `go-ship-it` fails with "command not found", retry from the control root with `uv run go-ship-it` before reporting a setup problem.

Examples below use `go-ship-it` for readability. In this GoShipit development repo, prefer `uv run go-ship-it` unless the package has been installed on PATH.

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

Do not continue lifecycle work from an arbitrary target repo checkout. Target repo code changes happen inside the active issue worktree only after `go-ship-it show-run <repo>/<issue-id>` confirms the worktree path.

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

## User Communication

Use the CLI as plumbing. When talking to the user, summarize the next action in plain language first. Show exact commands only when the user asks, when a command failed, or when the command is the safest way to disambiguate what will happen.

Good user-facing phrasing:

- "ParaWave is registered and has no active issues. Next I can create the first todo or update repo context."
- "This issue is active in an isolated worktree. I will inspect the run, then read the target repo context before editing."
- "The run is ready for review. I can write the handoff and export the issue-local evidence snapshot before cleanup."

## Skill Routing

Keep the agent-facing skill surface small:

- `manage-issues` when initializing a control root, registering a repo, creating a todo, starting work, checking status, or cleaning up an active issue.
- `work-issue` when investigating, proposing, implementing, testing, reviewing, or recording run evidence inside an active issue.

## Product Boundary

GoShipit does not automatically launch headless agents, discover work, create PRs, or integrate with GitHub or Jira in the local-first package path.

Remote integrations are optional future extensions. Keep local lifecycle evidence useful without them.

## Dogfood And Feedback Routing

In this development workspace, `parawave` may be registered as a dogfood target repo. Treat `state/repos/parawave/repo.yaml` and `state/repos/parawave/context.md` as the source of truth before starting ParaWave work. Do not present ParaWave as a default target repo for external users.

If ParaWave is not registered yet in this development workspace, set it up as the dogfood target:

```sh
scripts/setup/parawave.sh
```

Equivalent explicit setup:

```sh
go-ship-it init \
  --repo-id parawave \
  --repo-path <parawave-repo-path> \
  --test-command "uv run --extra dev --extra sqlite pytest tests/ -v --tb=short" \
  --feedback-repo-path <go-ship-it-repo-path> \
  --feedback-test-command "uv run pytest -q"
```

When GoShipit itself is being improved, use the registered `go-ship-it` repo. If the user reports GoShipit friction, confusing behavior, install problems, bad command output, or lifecycle UX issues while working any target repo, create or offer to create a normal todo issue under `go-ship-it`. Link it back to the source repo, source issue, active run path, and a concise note about what happened.

Do not create a separate feedback, learning, or observation folder for GoShipit product issues. Use the same repo-centric issue lifecycle so the feedback can be investigated, implemented, tested, archived, and exported like any other issue.

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
go-ship-it handoff <repo>/<issue-id> --write
# or, inside the managed worktree:
go-ship-it handoff --current --write
```
