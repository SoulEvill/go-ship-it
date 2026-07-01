# GoShipit Run Evidence: issue-003

## Issue

Source: `state/issues/execution/issue-003.md`

```markdown
---
id: issue-003
repo: parawave
status: execution
phase: test
title: Make validation errors deterministic and easier to read
created_at: '2026-06-30T17:12:19-07:00'
worktree: worktrees/parawave/issue-003
branch: go-ship-it/issue-003
claimed_by: parawave-real-enhancement-dogfood
started_at: '2026-06-30T17:12:22-07:00'
last_activity_at: '2026-06-30T17:14:46-07:00'
---

## Problem

Parawave validation errors currently render raw Python sets for unexpected and missing keys, which can be order-unstable and less readable.

## Context

Target parawave/validation.py and tests/test_validation.py. Keep the change small and avoid broader Parawave architecture changes.

## Acceptance Criteria

- Unexpected key errors list keys in sorted deterministic order.
- Missing required argument errors list keys in sorted deterministic order.
- Accepted function parameters in the unexpected-key error are listed in sorted deterministic order.
- Targeted validation tests and the configured Parawave test check pass.
```

## Run Metadata

```yaml
issue_id: issue-003
repo: parawave
branch: go-ship-it/issue-003
worktree: worktrees/parawave/issue-003
claimed_by: parawave-real-enhancement-dogfood
phase: test
started_at: '2026-06-30T17:12:22-07:00'
last_activity_at: '2026-06-30T17:14:46-07:00'
```

## Journal

## Phase: investigate

Timestamp: 2026-06-30T17:12:40-07:00
Phase: investigate

Investigating Parawave validation error messages for deterministic key formatting.

## Investigation

Timestamp: 2026-06-30T17:12:48-07:00
Phase: investigate

validate_inputs currently formats unexpected keys, accepted parameters, and missing arguments by interpolating Python sets directly. This is less readable and can produce unstable ordering in messages. The narrow fix is to add a helper that sorts names and joins them with comma separators.

## Phase: propose

Timestamp: 2026-06-30T17:12:48-07:00
Phase: propose

Proposing a narrow deterministic formatting helper for validation parameter names.

## Proposal

Timestamp: 2026-06-30T17:12:53-07:00
Phase: propose

Add a private _format_names helper in parawave/validation.py that returns sorted names joined by ', ', with '(none)' for empty sets. Use it for unexpected key, accepted parameter, and missing required argument messages. Add exact tests in tests/test_validation.py for sorted unexpected keys, sorted accepted parameters, and sorted missing arguments.

## Phase: implement

Timestamp: 2026-06-30T17:14:19-07:00
Phase: implement

Implemented deterministic validation key formatting in the Parawave worktree.

## Implementation

Timestamp: 2026-06-30T17:14:20-07:00
Phase: implement

Changed parawave/validation.py to format name sets with a sorted comma-separated helper. Added exact tests in tests/test_validation.py for sorted unexpected keys, accepted parameters, and missing required arguments.

## Phase: test

Timestamp: 2026-06-30T17:14:46-07:00
Phase: test

Running targeted validation tests and configured Parawave checks.

## Check: setup

Timestamp: 2026-06-30T17:14:56-07:00
Phase: test

Command: `env -u VIRTUAL_ENV uv sync --extra dev`

Exit code: 0

Evidence: `state/runs/issue-003/commands/2026-06-30T17-14-56-07-00-setup.yaml`

## Check: test

Timestamp: 2026-06-30T17:15:20-07:00
Phase: test

Command: `env -u VIRTUAL_ENV uv run --extra dev pytest -q`

Exit code: 0

Evidence: `state/runs/issue-003/commands/2026-06-30T17-15-06-07-00-test.yaml`

## Review

Timestamp: 2026-06-30T17:16:00-07:00
Phase: test

Targeted validation tests passed and configured setup/test checks passed through GoShipit run-check. The target change is ready for human review or optional Parawave branch integration.

## Command Records

### 2026-06-30T17-14-56-07-00-setup.yaml

- Check: `setup`
- Command: `env -u VIRTUAL_ENV uv sync --extra dev`
- CWD: `worktrees/parawave/issue-003`
- Exit Code: `0`
- Started: `2026-06-30T17:14:56-07:00`
- Ended: `2026-06-30T17:14:56-07:00`

Stdout tail:

```text

```

Stderr tail:

```text
Resolved 184 packages in 0.56ms
Audited 82 packages in 0.06ms
```

### 2026-06-30T17-15-06-07-00-test.yaml

- Check: `test`
- Command: `env -u VIRTUAL_ENV uv run --extra dev pytest -q`
- CWD: `worktrees/parawave/issue-003`
- Exit Code: `0`
- Started: `2026-06-30T17:15:06-07:00`
- Ended: `2026-06-30T17:15:20-07:00`

Stdout tail:

```text
........................................................................ [ 16%]
........................................................................ [ 32%]
........................................................................ [ 48%]
........................................................................ [ 64%]
........................................................................ [ 80%]
........................................................................ [ 96%]
...............                                                          [100%]
447 passed in 14.03s
```

Stderr tail:

```text

```

## Worktree

- Repo: `parawave`
- Branch: `go-ship-it/issue-003`
- Worktree: `worktrees/parawave/issue-003`

## Notes

Generated by `go-ship-it export-run`. Command records preserve recorded exit codes.
