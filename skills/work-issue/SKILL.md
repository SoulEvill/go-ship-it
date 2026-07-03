---
name: work-issue
description: Use when investigating, proposing, implementing, testing, reviewing, or recording evidence for an active GoShipit issue.
---

# Work Issue

## When To Use

Use after `manage-issues` starts an issue and creates an isolated worktree.

Do not use for creating, starting, or cleaning up issues. Use `manage-issues` for those state moves.

## Orientation

Before reading or editing target repo files, run:

```sh
go-ship-it show-issue <issue-id>
go-ship-it show-run <issue-id>
```

Confirm the active worktree path. Target repo edits belong only inside that worktree.

If working from inside the target worktree, inspect `.go-ship-it/context.yaml` when present. The context file records the issue id, control root, run dir, claim label, and claim id for this run.

Inside that managed worktree, run-bound commands can omit the issue id. Use `--current` when you want the command to be explicit. GoShipit verifies `.go-ship-it/context.yaml` against `state/runs/<issue-id>/run.yaml` before writing evidence.

```sh
go-ship-it status
go-ship-it show-run
go-ship-it show-issue --current
go-ship-it show-run --current
```

Also read the target repo context when it exists:

```text
state/repos/<repo>/context.md
```

Use `references/workflow-notes-template.md` when writing evidence notes.

## Phase Commands

Investigation:

```sh
go-ship-it set-phase <issue-id> investigate --note "<why investigation started or resumed>"
go-ship-it append-note <issue-id> --section "Investigation" --phase investigate --note "<findings>"
# inside the managed worktree:
go-ship-it set-phase --current investigate --note "<why investigation started or resumed>"
go-ship-it append-note --current --section "Investigation" --phase investigate --note "<findings>"
```

Proposal:

```sh
go-ship-it set-phase <issue-id> propose --note "<investigation summary>"
go-ship-it append-note <issue-id> --section "Proposal" --phase propose --note "<proposal>"
# inside the managed worktree:
go-ship-it set-phase --current propose --note "<investigation summary>"
go-ship-it append-note --current --section "Proposal" --phase propose --note "<proposal>"
```

Implementation:

```sh
go-ship-it set-phase <issue-id> implement --note "<implementation started>"
go-ship-it append-note <issue-id> --section "Implementation" --phase implement --note "<changed files and decisions>"
# inside the managed worktree:
go-ship-it set-phase --current implement --note "<implementation started>"
go-ship-it append-note --current --section "Implementation" --phase implement --note "<changed files and decisions>"
```

Test and review:

```sh
go-ship-it set-phase <issue-id> test --note "<ready for checks>"
go-ship-it run-check <issue-id> --check setup
go-ship-it run-check <issue-id> --check test
go-ship-it run-check <issue-id> --check lint
go-ship-it append-note <issue-id> --section "Review" --phase test --note "<review findings and readiness>"
# inside the managed worktree:
go-ship-it set-phase --current test --note "<ready for checks>"
go-ship-it run-check --current --check test
go-ship-it append-note --current --section "Review" --phase test --note "<review findings and readiness>"
```

Process trace:

```sh
go-ship-it append-log <issue-id> --note "<process observation>" --source <pointer>
# inside the managed worktree:
go-ship-it append-log --current --note "<process observation>" --source <pointer>
```

Explicit handoff:

```sh
go-ship-it show-run <issue-id> --handoff
go-ship-it handoff <issue-id> --write
# inside the managed worktree:
go-ship-it show-run --handoff
go-ship-it handoff --write
go-ship-it show-run --current --handoff
go-ship-it handoff --current --write
```

## State Boundaries

Allowed state writes:

- set current phase
- append journal notes
- record configured command evidence
- append lightweight run logs

Allowed target repo writes:

- none during investigation, proposal, or review-only work
- only files inside the active issue worktree during implementation or requested review fixes

## Human Gates

Ask for approval before implementation when the change affects behavior, public APIs, data formats, release workflow, or scope beyond the proposal.

Ask before skipping a failing check or treating a review finding as intentional.

## Readiness

Before saying the issue is ready for cleanup, compare acceptance criteria against concrete evidence. Passing tests are useful but not always sufficient; call out any criterion that lacks a matching test, command record, or review note.

When the user wants another session to continue, create a handoff with `go-ship-it handoff <issue-id> --write`, or `go-ship-it handoff --write` from the managed worktree, and tell them the file path.

## Failure Behavior

Leave the issue in execution and report the blocker, missing context, or failing evidence.
