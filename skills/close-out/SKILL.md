---
name: close-out
description: "Use when shipping a reviewed GoShipit issue: preparing the local PR preview, publishing the PR, or archiving the finished issue."
---

# Close Out

## When To Use

Use after `work-issue` finishes the review phase and `verify-run --strict` is clean.

Do not use for build work (investigate/propose/implement/review) — that is `work-issue`. Do not use for returning an issue to todo — that is `manage-issues`.

## Orientation

```sh
go-ship-it show-run <repo>/<issue-id>
go-ship-it verify-run <repo>/<issue-id> --strict
```

Use the resolved GoShipit command from `using-go-ship-it`. In this development checkout that is usually `uv run go-ship-it`.

## The Three Gates

Close-out is three separate gates, crossed in order, never bundled:

1. **prepare-pr** (reversible, local) — write the PR preview. Read `references/phases/write-pr.md`; edit only that contract to change PR shape.

```sh
go-ship-it prepare-pr <repo>/<issue-id> --branch <team-branch-name>
```

The first `prepare-pr` needs `--branch`; reruns reuse the recorded branch. This writes `pr.md` beside the run files, records the PR branch in `run.yaml`, and moves the phase to `prepare-pr`. Stop here and show the user `pr.md` and `evidence.md`.

2. **publish** (irreversible: pushes and opens a PR) — read `references/phases/publish.md`.

```sh
go-ship-it publish-pr <repo>/<issue-id> --approved
```

Run only after the user approves publishing (or `pull_request.auto_publish: true`). Publishing is mechanically blocked while `verify-run` reports any finding — there is no override; fix the evidence instead. Repos with `pull_request.provider: none` never publish: the reviewed local `pr.md` is their final gate.

3. **archive** (terminal: no reopen or unarchive) — read `references/phases/archive.md`.

```sh
go-ship-it export-run <repo>/<issue-id>
go-ship-it cleanup-issue <repo>/<issue-id> --destination archive --confirm --note "<final note>" --remove-worktree
```

Ask the user before archiving. Never bundle archive with publish in a single step. If the worktree has uncommitted changes, cleanup refuses to remove it; commit first or archive without `--remove-worktree` to preserve it for inspection.

## Failure Behavior

If any gate refuses (verify findings, dirty worktree, missing approval), stop, report the exact blocker, and leave the issue in execution.
