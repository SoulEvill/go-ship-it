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

- `uv run pytest -v`: 81 passed in 2.72s.
- Dev Parawave fixture wrapper: exited 0 and printed `Report: /var/folders/jl/h_k_sm9n12x0xwm2c094w8km0000gn/T/go-ship-it-target-e2e-20260630T223432Z-uuomrud2/report.md`.
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

Repos: 1
Todo: 0
Execution: 0
Archive: 1
Runs: 1
Managed Worktrees: 0

Summary: 0 errors, 1 warnings, 4 ok
```

The warning was expected for this disposable run:

```text
- repo/parawave: lint_command is not configured (repo.lint_command_missing)
```

## Notes

The generic harness required explicit target values. The dev wrapper supplied Parawave values only for GoShipit contributor dogfooding. The source Parawave repo remained clean.

The first wrapper attempt inside the sandbox failed before registration because `uv` could not access `/Users/zhengisamazing/.cache/uv/sdists-v9/.git`. Rerunning the same wrapper outside the sandbox succeeded.
