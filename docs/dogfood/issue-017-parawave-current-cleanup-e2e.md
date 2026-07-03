# Issue 017: Parawave Current-Run and Cleanup E2E

## Scope

Ran the disposable Parawave target harness after the repo-context/current-run cleanup.

## Runs

- Preserved active run:
  - Report: `/var/folders/jl/h_k_sm9n12x0xwm2c094w8km0000gn/T/go-ship-it-target-e2e-20260703T055943Z-v2xyx_d4/report.md`
  - Result: success
  - Final status: `Execution: 1`, `Archive: 0`, `Managed Worktrees: 1`, active phase `test`
- Cleanup/archive run:
  - Report: `/var/folders/jl/h_k_sm9n12x0xwm2c094w8km0000gn/T/go-ship-it-target-e2e-20260703T060026Z-9acoy1zu/report.md`
  - Result: success
  - Final status: `Execution: 0`, `Archive: 1`, `Managed Worktrees: 0`

## Current-Run Smoke

From a preserved managed Parawave worktree, these worked without passing an issue id:

```sh
go-ship-it status
go-ship-it show-run
go-ship-it append-log --note "Manual current-run smoke from preserved Parawave worktree." --source manual:parawave-current-smoke
go-ship-it handoff --write
go-ship-it verify-run --current
go-ship-it run-check --current --check test
```

`status` now displays the active worktree branch plus current issue, worktree, run branch, and claim id.

## Notes

- The first current-run `run-check --current --check test` failed under sandboxed execution because uv could not read its cache. The same command passed with cache access allowed.
- `doctor` reports one expected warning for Parawave harness runs: `repo.lint_command_missing`, because the disposable harness only registers setup and test commands.
- The target harness now calls `set-phase` before proposal/test evidence so final status reaches `Phase: test`.
