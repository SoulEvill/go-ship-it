---
name: manage-issues
description: Use when initializing GoShipit, registering a target repo, creating todo issues, starting issues, checking status, or cleaning up active issues.
---

# Manage Issues

## When To Use

Use for lifecycle state changes around issues: initialize, register, add, start, status, and cleanup.

Use `work-issue` after an issue is active and the task is investigation, proposal, implementation, testing, review, or evidence writing.

## Orientation

Start from the GoShipit control root:

```sh
go-ship-it status
go-ship-it list-issues
go-ship-it show-issue <repo>/<issue-id>
```

Use the resolved GoShipit command from `using-go-ship-it`. In this development checkout that is usually `uv run go-ship-it`; in an installed package it is usually `go-ship-it`.

If root or package setup is uncertain, also run:

```sh
go-ship-it doctor
```

Read `references/state-lifecycle.md` for state movement rules.

When speaking to the user, describe lifecycle intent first and keep raw commands mostly hidden. It is fine to run the CLI as plumbing. Show exact commands only when the user asks to run them manually, when a command fails, or when command text is needed for handoff/debugging.

If the user asks for preflight during setup or before starting work, run the normal orientation and consistency checks (`status` and `doctor`) and summarize the result. Preflight is a user-facing routine, not a separate lifecycle state.

## Core Commands

```sh
go-ship-it init
go-ship-it register-repo <repo> <local-path-or-git-url> --test-command <cmd>
go-ship-it update-repo <repo> --worktree-setup-command <cmd>
go-ship-it add-issue --repo <repo> --title <title> --problem <problem> --context <context> --acceptance <criterion>
go-ship-it start-issue <repo>/<issue-id> --claimed-by <thread-label>
go-ship-it cleanup-issue <repo>/<issue-id> --destination todo --note <note> --remove-worktree
go-ship-it cleanup-issue <repo>/<issue-id> --destination archive --note <note> --remove-worktree
```

When the user is using the control root to improve GoShipit itself, register a feedback repo target too:

```sh
go-ship-it init
go-ship-it register-repo <target-repo> <target-path-or-git-url> --test-command <target-test-command>
go-ship-it register-repo go-ship-it <go-ship-it-repo-path-or-git-url> --feedback --test-command "uv run pytest -q"
```

This creates `state/repos/go-ship-it/` with GoShipit product-feedback context. Use it for issues about GoShipit behavior, setup friction, confusing lifecycle UX, or agent/package integration gaps.

If the user explicitly asks to set up ParaWave in the GoShipit development workspace, prefer the helper:

```sh
scripts/setup/parawave.sh
```

It registers `parawave` as a normal target repo and `go-ship-it` as the feedback repo.

`--claimed-by` is optional. When omitted, GoShipit creates a stable local actor label from the agent/tool environment, user, host, control root, and current working directory.

`start-issue` prints the worktree, run file, claim label, deterministic claim id, and context file. If the issue is already active, it returns the existing active run details instead of creating another worktree.

For normal completed work, include `--remove-worktree` when archiving so the control root stays clean. Cleanup refuses to remove a dirty managed worktree by default; commit/prepare the PR first, or omit `--remove-worktree` when the user wants to preserve the worktree for inspection. Use `--discard-worktree-changes` only when the user explicitly says to throw away local target changes.

Repo registration writes a folder, not a single flat registry file:

```text
state/repos/<repo>/
  repo.yaml
  context.md
  issues/
    todo/<issue-id>/issue.md
    execution/<issue-id>/
      issue.md
      run.yaml
      notes.md
      logs/
        events.jsonl
        commands/*.yaml
    archive/<issue-id>/issue.md
```

Use `repo.yaml` for machine config and `context.md` for repo-wide background that should be available to future issues. Issue ids are repo-local, so explicit issue references use `<repo>/<issue-id>`.

Repo sources may be local paths or Git URLs. Local paths use that local checkout as the source for new issue worktrees. URL sources are cloned once into `worktrees/<repo>/_source`; active issue worktrees are siblings such as `worktrees/<repo>/issue-001`. Do not edit `_source` during issue work.

Current source freshness behavior is intentionally simple: GoShipit does not automatically fetch or pull a registered source before starting an issue. A Git URL source can become stale if the remote changes after registration. A local source can also be stale if the user's local branch is behind its remote. If the user cares about starting from the latest upstream state, mention that the registered source should be refreshed before starting the issue.

If every issue worktree needs local files or bootstrap work, configure one repo-level `worktree_setup.command` with `update-repo --worktree-setup-command`. This automatic bootstrap command runs from each new issue worktree after creation. Use it for repeatable setup such as copying ignored local config, creating generated files, or running dependency bootstrap. If it fails, stop and show the user the recorded command evidence path.

Do not confuse that bootstrap with manual repo checks. `setup_command`, `test_command`, and `lint_command` are validation commands invoked later with `run-check --check setup|test|lint`.

When registering a repo or before starting its first issue, ask whether the target repo needs ignored local files or bootstrap steps in each worktree: `.env`, credentials placeholders, generated config, local fixtures, dependency sync, or private package setup. If yes, help the user define a repeatable `worktree_setup.command`; do not invent repo-specific setup by guessing.

## State Boundaries

State changes must go through the CLI. Do not move issue files manually except for explicit repair work after `doctor` identifies the problem.

Allowed state writes:

- create todo issue files through `add-issue`
- move todo issues into execution through `start-issue`
- create run metadata and claim lock through `start-issue`
- write `.go-ship-it/context.yaml` inside the managed worktree through `start-issue`
- move execution issues to todo or archive through `cleanup-issue`
- append cleanup notes through `cleanup-issue`

Target repo writes are not allowed, except Git worktree creation/removal performed by GoShipit commands.

## Human Gates

Ask the user when repo id, target repo source, whether worktrees need local setup, issue title, acceptance criteria, cleanup destination, or worktree removal is unclear.

If `start-issue` reports an issue is already active, show the existing run details and ask whether the user wants to continue that active run.

## Failure Behavior

If bare `go-ship-it` is not found, retry with the resolved development command before reporting failure. For other errors, report the CLI error and stop. Do not edit target repo files or manually patch state as a shortcut.
