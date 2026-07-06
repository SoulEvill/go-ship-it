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
go-ship-it show-issue <repo>/<issue-id>
go-ship-it show-run <repo>/<issue-id>
```

Use the resolved GoShipit command from `using-go-ship-it`. In this development checkout that is usually `uv run go-ship-it`; in an installed package it is usually `go-ship-it`.

Confirm the active worktree path. Target repo edits belong only inside that worktree.

If working from inside the target worktree, inspect `.go-ship-it/context.yaml` when present. The context file records the issue id, control root, run dir, claim label, and claim id for this run.

Inside that managed worktree, run-bound commands can omit the issue ref. Use `--current` when you want the command to be explicit. GoShipit verifies `.go-ship-it/context.yaml` against `state/repos/<repo>/issues/execution/<issue-id>/run.yaml` before writing notes or command records.

If `start-issue` reports a failed worktree setup command, stop and inspect the recorded command evidence before editing. The issue remains active in setup phase so the setup failure can be fixed or the work returned to todo.

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

When speaking to the user, describe work progress in lifecycle terms instead of exposing the CLI transcript. Say what you found, what phase the issue is in, what evidence was recorded, and what decision is needed. Show exact command text only when the user asks, when a command fails, or when preparing a handoff/debug record.

## Development Method

GoShipit owns the lifecycle, isolation, and evidence. It does not need to own the coding methodology.

For development tasks, prefer a test-first loop when practical:

- During investigation, identify the behavior to prove and the most meaningful validation boundary.
- During proposal, state whether a failing test, regression test, property/contract check, or manual acceptance check should come before implementation.
- Before implementation, offer the user a choice when the test-first path is non-trivial or could add meaningful scope.
- If a Superpowers-style TDD/debugging skill is available in the agent environment and the user wants that rigor, use it for the coding loop inside the active GoShipit worktree.
- If the task is docs-only, config-only, exploratory, or too small for formal TDD, keep it lightweight but still record the acceptance evidence.

Whatever methodology is used, record the result back into GoShipit with phase notes, check records, handoff, and readiness verification.

## Phase Commands

Investigation:

```sh
go-ship-it set-phase <repo>/<issue-id> investigate --note "<why investigation started or resumed>"
go-ship-it append-note <repo>/<issue-id> --section "Investigation" --for-phase investigate --note "<findings>"
# inside the managed worktree:
go-ship-it set-phase --current investigate --note "<why investigation started or resumed>"
go-ship-it append-note --current --section "Investigation" --for-phase investigate --note "<findings>"
```

Proposal:

```sh
go-ship-it set-phase <repo>/<issue-id> propose --note "<investigation summary>"
go-ship-it append-note <repo>/<issue-id> --section "Proposal" --for-phase propose --note "<proposal>"
# inside the managed worktree:
go-ship-it set-phase --current propose --note "<investigation summary>"
go-ship-it append-note --current --section "Proposal" --for-phase propose --note "<proposal>"
```

Implementation:

```sh
go-ship-it set-phase <repo>/<issue-id> implement --note "<implementation started>"
go-ship-it append-note <repo>/<issue-id> --section "Implementation" --for-phase implement --note "<changed files and decisions>"
# inside the managed worktree:
go-ship-it set-phase --current implement --note "<implementation started>"
go-ship-it append-note --current --section "Implementation" --for-phase implement --note "<changed files and decisions>"
```

Test and review:

```sh
go-ship-it set-phase <repo>/<issue-id> test --note "<ready for checks>"
go-ship-it run-check <repo>/<issue-id> --check setup
go-ship-it run-check <repo>/<issue-id> --check test
go-ship-it run-check <repo>/<issue-id> --check lint
go-ship-it append-note <repo>/<issue-id> --section "Review" --for-phase test --note "<review findings and readiness>"
# inside the managed worktree:
go-ship-it set-phase --current test --note "<ready for checks>"
go-ship-it run-check --current --check test
go-ship-it append-note --current --section "Review" --for-phase test --note "<review findings and readiness>"
```

Readiness before cleanup:

```sh
go-ship-it handoff <repo>/<issue-id> --write
go-ship-it export-run <repo>/<issue-id>
go-ship-it verify-run <repo>/<issue-id> --strict
go-ship-it prepare-pr <repo>/<issue-id> --branch <team-branch-name>
# inside the managed worktree:
go-ship-it handoff --write
go-ship-it export-run --current
go-ship-it verify-run --current --strict
go-ship-it prepare-pr --current --branch <team-branch-name>
```

Treat `go-ship-it verify-run --strict` as the readiness gate before normal archive cleanup. It fails on warnings such as missing handoff context, failed or missing command evidence, and acceptance criteria that are not explicitly matched to evidence. If strict verification does not pass, leave the issue in execution unless the user explicitly accepts the remaining warnings.

Before claiming the issue is done, use the agent platform's native sub-agent, reviewer, or checker mechanism when available. Give the checker the issue problem, acceptance criteria, relevant diff, GoShipit notes, and command evidence. Ask it to judge whether the work satisfies the acceptance criteria and to call out caveats, missing tests, or scope drift. Record the checker result in the Review note. This is the semantic done/not-done judgment; `verify-run --strict` remains the deterministic evidence-structure gate.

Before archive cleanup, make sure the target work is preserved in the way the user wants. If the worktree has uncommitted changes, cleanup with `--remove-worktree` will refuse to delete it. Commit/prepare the PR, archive without removing the worktree for review, or use `--discard-worktree-changes` only after the user explicitly chooses to throw away local work.

`prepare-pr` is local-only. It writes `pr.md` beside the issue run files and records the issue-level PR branch in `run.yaml`. The managed local branch can stay as `go-ship-it/<issue-id>`. The PR branch should be chosen for that issue using the target repo team's convention. The first `prepare-pr` needs `--branch <branch>`; later reruns can omit it to reuse the recorded branch.

Only run `publish-pr --approved` after the user approves publishing, unless `state/repos/<repo>/repo.yaml` has `pull_request.auto_publish: true`. Publishing uses the native GitHub path: push the local work branch to the recorded PR branch, then create the PR with `gh pr create --body-file pr.md`.

Generated trace:

```sh
go-ship-it show-run <repo>/<issue-id> --trace
# inside the managed worktree:
go-ship-it show-run --current --trace
```

When the user reports GoShipit friction, confusing behavior, missing setup, or bad UX, create or offer to create a normal issue under the `go-ship-it` repo. Link it back to the source repo, issue, and run where it was observed.

Explicit handoff:

```sh
go-ship-it show-run <repo>/<issue-id> --handoff
go-ship-it handoff <repo>/<issue-id> --write
# inside the managed worktree:
go-ship-it show-run --handoff
go-ship-it handoff --write
go-ship-it show-run --current --handoff
go-ship-it handoff --current --write
```

## State Boundaries

Allowed state writes:

- set current phase
- append authored notes
- record configured command logs
- write explicit handoff files

Allowed target repo writes:

- none during investigation, proposal, or review-only work
- only files inside the active issue worktree during implementation or requested review fixes

## Human Gates

Ask for approval before implementation when the change affects behavior, public APIs, data formats, release workflow, or scope beyond the proposal.

Ask before skipping a failing check or treating a review finding as intentional.

## Readiness

Before saying the issue is ready for cleanup, compare acceptance criteria against concrete evidence. Passing tests are useful but not always sufficient; call out any criterion that lacks a matching test, command record, or review note.

Record that mapping in the Review section. Include the independent checker result when one was available: verdict, caveats, and whether any follow-up is needed. Use phrasing close to the acceptance criteria so `verify-run --strict` can find the evidence without guessing.

When the user wants another session to continue, create a handoff with `go-ship-it handoff <repo>/<issue-id> --write`, or `go-ship-it handoff --write` from the managed worktree, and tell them the file path.

## Failure Behavior

Leave the issue in execution and report the blocker, missing context, or failing evidence.
