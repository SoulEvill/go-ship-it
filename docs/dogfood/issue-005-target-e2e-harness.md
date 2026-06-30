# Target E2E Harness Dogfood

Date: 2026-06-30

## Commands

```bash
uv run pytest -v
git -C ../parawave status --short --branch
scripts/dev/run-parawave-e2e.sh --cleanup-worktree
git -C ../parawave status --short --branch
```

## Result

- `uv run pytest -v`: 84 passed in 2.81s.
- Dev Parawave fixture wrapper: exited 0 and printed `Report: /var/folders/jl/h_k_sm9n12x0xwm2c094w8km0000gn/T/go-ship-it-target-e2e-20260630T225528Z-wo0t_g9g/report.md`.
- Parawave source status before:

```text
## main...origin/main
```

- Parawave source status after:

```text
## main...origin/main
```

## Harness Report Excerpt

```text
Result: `success`
Started at: `2026-06-30T22:55:28.319072+00:00`
Finished at: `2026-06-30T22:55:44.331261+00:00`

Repos: 1
Todo: 0
Execution: 0
Archive: 1
Runs: 1
Managed Worktrees: 0

Summary: 0 errors, 1 warnings, 4 ok

Final State and Exported Issue sections were present in the report.
Exported issue path: `/var/folders/jl/h_k_sm9n12x0xwm2c094w8km0000gn/T/go-ship-it-target-e2e-20260630T225528Z-wo0t_g9g/exported-run.md`
```

The warning was expected for this disposable run:

```text
- repo/parawave: lint_command is not configured (repo.lint_command_missing)
```

## Notes

The generic harness required explicit target values. The dev wrapper supplied Parawave values only for GoShipit contributor dogfooding. The source Parawave repo remained clean.

The first wrapper attempt inside the sandbox failed before registration because `uv` could not access `/Users/zhengisamazing/.cache/uv/sdists-v9/.git`. Rerunning the same wrapper outside the sandbox succeeded.
