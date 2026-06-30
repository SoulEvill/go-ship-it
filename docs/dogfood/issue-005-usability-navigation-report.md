# GoShipit Usability And Navigation Report

Date: 2026-06-30

## User Path Observed

- Start from `README.md`, which explains GoShipit as a local-first control repo and points development users to `uv sync`, `uv run pytest -v`, and `uv run go-ship-it --help`.
- Install or run from a clone with `uv tool install .` or `uv run go-ship-it`.
- Run the first health checks from `README.md` or `docs/user-e2e.md`: `go-ship-it doctor` and `go-ship-it status`.
- Inspect the command list with `go-ship-it --help`. The top-level help exposes the lifecycle verbs: `register-repo`, `add-issue`, `start-issue`, `append-note`, `set-phase`, `run-check`, `cleanup-issue`, navigation commands, `doctor`, and `export-run`.
- Register a target repo before issue work. `docs/user-e2e.md` currently starts the issue flow with `go-ship-it show-repo <repo>`, so a new user must infer registration from `go-ship-it --help`, prior setup, or the disposable target harness docs.
- Create a todo issue with `go-ship-it add-issue --repo <repo> --title <title> --problem <problem>`, optionally adding `--context` and `--acceptance`.
- Claim work with `go-ship-it start-issue <issue-id> --claimed-by <name>`. The command prints the worktree path, and the user is expected to move implementation work there.
- Use `show-issue`, `show-run`, and `status` to orient around issue state, run state, and preserved worktrees.
- Record evidence with `set-phase`, `append-note`, and `run-check`, then export with `export-run`.
- Finish by using `cleanup-issue` to archive or return work to todo, then run `doctor` again.
- For repeatable local smoke testing, use `scripts/run-target-e2e.py` with explicit target values, or the contributor-only `scripts/dev/run-parawave-e2e.sh` fixture inside this workspace.

## Navigation Strengths

- `go-ship-it --help` presents the main command surface in lifecycle order well enough to identify the available verbs.
- `docs/user-e2e.md` gives a compact end-to-end checklist from health check through cleanup.
- The disposable target harness makes the happy path repeatable and writes a durable Markdown report with command records, stdout, stderr, exit codes, and final status.
- `status` output is a strong daily orientation point because it summarizes repo count, todo, execution, archive, runs, managed worktrees, active issues, and preserved worktrees.
- `doctor` gives a clear health summary with errors, warnings, and ok checks. In the Parawave dogfood run it reported `0 errors, 1 warnings, 4 ok`.
- The target harness keeps the generic path target-agnostic: users must provide `--target-id`, `--target-path`, `--setup-command`, and `--test-command`.

## Navigation Gaps

- The individual help pages are too terse. `status --help` only shows `usage: go-ship-it status [-h]`, and `start-issue --help` does not explain that the printed value is the worktree path.
- `docs/user-e2e.md` says to inspect a registered repo with `show-repo`, but it does not show the first-time `register-repo` command before the issue flow.
- The top-level help lists many commands but does not group them by phase, navigation, evidence, or cleanup, so the intended order is easier to learn from docs than from CLI help.
- `add-issue --help` lists required flags but does not include a minimal example or explain what the resulting issue id/path means.
- `doctor --help` exposes `--strict`, but the behavior is only obvious after seeing dogfood docs: warnings are acceptable normally and become non-zero in strict mode.
- The external-user path still depends on knowing when to use the generated worktree rather than the original target repo.
- The harness report is clear after the run, but the CLI does not yet provide a single "next command" affordance at each lifecycle step.

## Before External User E2E

- Add a first-time setup section to `docs/user-e2e.md` with a complete `register-repo` example and a `show-repo` verification step.
- Add examples to `add-issue --help`, `start-issue --help`, `run-check --help`, and `cleanup-issue --help`.
- Make `start-issue` output label the returned path, for example `Worktree: <path>`, so users know what to open next.
- Add a short "normal path" section to the top-level help or docs: register repo, add issue, start issue, implement in worktree, record evidence, run checks, export, cleanup.
- Clarify `doctor --strict` in docs and help so users know it is intended for CI-like verification, not every exploratory local run.
- Consider a `next` or `guide` command that summarizes the current workspace state and recommends the next likely command.
- Run the external user e2e against a repo that is not Parawave and not preconfigured, to prove the generic path is understandable without fixture knowledge.

## Product Questions

- Should `go-ship-it init` also offer or print the next `register-repo` command shape?
- Should `register-repo` require setup and test commands, or is optional command configuration acceptable for first-time users?
- Should `start-issue` print both the worktree path and suggested follow-up commands like `show-run`, `append-note`, and `run-check`?
- Should `status` include stale preserved worktree warnings directly, or should that remain only in `doctor`?
- Should the disposable target harness live only as a developer script, or should it become a documented smoke-test command with a stable CLI entry point?
- What is the minimum evidence GoShipit should require before `cleanup-issue --destination archive` feels complete enough for external users?
