# Parawave Dogfood Report: issue-001

## Issue

- Title: Clarify Parawave resume behavior in docs
- Repo: `parawave`
- Branch: `go-ship-it/issue-001`
- Archived issue file: `state/issues/archive/issue-001.md`
- Run metadata: `state/runs/issue-001/run.yaml`
- Journal: `state/runs/issue-001/journal.md`

## Worktree

- GoShipit-created worktree: `worktrees/parawave/issue-001`
- Preserved for inspection: yes
- Target change: `README.md`

The original Parawave checkout remained untouched. The docs change exists only in
the preserved worktree branch.

## Lifecycle Evidence

- Investigate: journal records relevant files, observed README gap, constraints, and open questions.
- Propose: journal records a small README clarification proposal and acceptance checks.
- Implement: journal records the README-only change.
- Test/review: command records and review note capture both registered check failure and manual confidence check.
- Cleanup: issue archived with the worktree preserved.

## Commands Run

- `go-ship-it run-check issue-001 --check test`
  - Evidence: `state/runs/issue-001/commands/2026-06-30T01-13-11-07-00-test.yaml`
  - Result: exit `2`
- `go-ship-it run-check issue-001 --check setup`
  - Evidence: `state/runs/issue-001/commands/2026-06-30T01-13-28-07-00-setup.yaml`
  - Result: exit `0`
- `go-ship-it run-check issue-001 --check test`
  - Evidence: `state/runs/issue-001/commands/2026-06-30T01-13-33-07-00-test.yaml`
  - Result: exit `2`
- Manual confidence check from `worktrees/parawave/issue-001`:
  - `env -u VIRTUAL_ENV uv run --extra dev pytest -q`
  - Result: `445 passed in 14.06s`

## Result

GoShipit successfully created the issue, created the target repo worktree,
recorded phase transitions, appended durable notes, captured command evidence,
and archived the run while preserving the target worktree.

The registered Parawave test command did not pass because `uv run pytest` used a
bare environment and missed dev/storage dependencies such as `aiofiles`. The
same worktree passed the full suite when run with dev extras explicitly.

## What Worked

- The new evidence commands made the run easy to audit without hand-editing state files.
- `run-check` captured failed command evidence honestly, including stdout/stderr tails and exit code.
- Preserving the worktree made the target README change easy to inspect after cleanup.

## What Felt Weak

- Repo command configuration needs to distinguish project setup for runtime use from setup for full test execution.
- The skills now point at templates, but they still rely on the agent to decide how much detail is enough.
- Runtime state is intentionally ignored, so reports need to reference state paths clearly.

## Recommended Next Step

Add a small command-inspection or repo-command update path so GoShipit can show
the registered setup/test/lint commands before a run and make command
misconfiguration easier to spot before test/review.
