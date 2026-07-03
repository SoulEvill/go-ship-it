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
go-ship-it show-issue <issue-id>
```

If root or package setup is uncertain, also run:

```sh
go-ship-it doctor
```

Read `references/state-lifecycle.md` for state movement rules.

## Core Commands

```sh
go-ship-it init --repo-id <repo> --repo-path <path> --test-command <cmd>
go-ship-it add-issue --repo <repo> --title <title> --problem <problem> --context <context> --acceptance <criterion>
go-ship-it start-issue <issue-id> --claimed-by <thread-label>
go-ship-it cleanup-issue <issue-id> --destination todo --note <note> --remove-worktree
go-ship-it cleanup-issue <issue-id> --destination archive --note <note>
```

`--claimed-by` is optional. When omitted, GoShipit creates a stable local actor label from the agent/tool environment, user, host, control root, and current working directory.

`start-issue` prints the worktree, run file, claim label, deterministic claim id, and context file. If the issue is already active, it returns the existing active run details instead of creating another worktree.

Repo registration writes a folder, not a single flat registry file:

```text
state/repos/<repo>/
  repo.yaml
  context.md
```

Use `repo.yaml` for machine config and `context.md` for repo-wide background that should be available to future issues.

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

Ask the user when repo id, target repo path, issue title, acceptance criteria, cleanup destination, or worktree removal is unclear.

If `start-issue` reports an issue is already active, show the existing run details and ask whether the user wants to continue that active run.

## Failure Behavior

Report the CLI error and stop. Do not edit target repo files or manually patch state as a shortcut.
