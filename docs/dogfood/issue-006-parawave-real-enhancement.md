# Parawave Real Enhancement Dogfood

Date: 2026-06-30

## Issue

- GoShipit issue id: `issue-003`
- Target repo: `parawave`
- Target branch: `go-ship-it/issue-003`
- Worktree: `worktrees/parawave/issue-003`

## Enhancement

Parawave validation errors now format unexpected keys, accepted function parameters, and missing required arguments in deterministic sorted order instead of rendering raw Python sets.

## Commands

```bash
uv run go-ship-it add-issue ...
uv run go-ship-it start-issue issue-003 --claimed-by parawave-real-enhancement-dogfood
env -u VIRTUAL_ENV uv run --extra dev pytest tests/test_validation.py -q
uv run go-ship-it run-check issue-003 --check setup
uv run go-ship-it run-check issue-003 --check test
uv run go-ship-it export-run issue-003 --output docs/dogfood/issue-006-parawave-real-enhancement-export.md
uv run go-ship-it cleanup-issue issue-003 --destination archive --note "Parawave deterministic validation error enhancement completed and evidence exported."
uv run go-ship-it doctor
```

## Results

- Added RED tests for deterministic unexpected-key and missing-required-argument messages. The first targeted run failed as expected because messages still contained Python set formatting.
- After implementation, targeted validation tests passed: `env -u VIRTUAL_ENV uv run --extra dev pytest tests/test_validation.py -q` returned `22 passed in 0.03s`.
- Parawave commit on the managed branch: `a503709 fix: make validation errors deterministic`.
- GoShipit setup check passed with exit code `0`; command record: `state/runs/issue-003/commands/2026-06-30T17-14-56-07-00-setup.yaml`.
- GoShipit test check passed with exit code `0`; command record: `state/runs/issue-003/commands/2026-06-30T17-15-06-07-00-test.yaml`.
- Configured Parawave test check result: `447 passed in 14.03s`.
- Exported evidence path: `docs/dogfood/issue-006-parawave-real-enhancement-export.md`.
- Issue cleanup moved `issue-003` to archive, and `show-run` reported phase `cleanup`.
- Final `go-ship-it status` reported `Todo: 0`, `Execution: 0`, `Archive: 2`, `Runs: 2`, and preserved worktree `parawave/issue-003`.
- Final `go-ship-it doctor` reported `0 errors, 4 warnings, 11 ok`.

## Rough Edges Observed

- Issue id handling was smooth because the CLI returned the created issue file path, but later commands still require manually carrying the id through each step.
- Worktree path discovery was clear after `start-issue` printed the absolute managed path; relative paths in later commands remained easy to use from the GoShipit repo.
- Phase and evidence commands were explicit and auditable, though the sequence creates several small commands for a short real change.
- Check commands worked well once run through `go-ship-it run-check`; the command records preserved setup and test commands, exit codes, timestamps, and output tails.
- Export happened before cleanup, so the export file records the run while the issue source was still in execution/test; the later `show-run` output is needed to see cleanup/archive evidence.
- Cleanup preserved the Parawave worktree for review, which is useful for target integration, but doctor warns about preserved inactive worktrees.
- Doctor warnings were actionable and non-blocking: Parawave has no configured lint command, `issue-001` has a preserved worktree without a matching issue file, and `issue-002`/`issue-003` have preserved inactive worktrees.
- Target integration remains a human decision. The Parawave branch is tested and available, but `../parawave/main` was not changed.

## Target Integration

The Parawave branch was tested. Merging into `../parawave/main` was not performed unless separately approved by the user.
