# User E2E Checklist

Run this before trying GitHub, PR, or Jira integrations.

## Preflight

```sh
go-ship-it doctor
go-ship-it status
```

In a clone-based GoShipit development checkout, use `uv run go-ship-it ...` if `go-ship-it` is not installed on PATH. In an installed package, use `go-ship-it ...`.

For a first-time control root, initialize state, then register the target repo:

```sh
go-ship-it init
go-ship-it register-repo my-repo /path/to/my-repo --test-command "uv run pytest"
```

For GoShipit contributors testing with ParaWave in this workspace, setup should register `parawave` as a normal target repo:

```sh
scripts/setup/parawave.sh
```

That helper runs `go-ship-it init`, registers `parawave` from `../parawave` with ParaWave's test command, and registers the local `go-ship-it` feedback repo. Set `PARAWAVE_PATH=/path/to/parawave` when the ParaWave clone is not a sibling of this repo.

Equivalent explicit command:

```sh
go-ship-it init
go-ship-it register-repo parawave /path/to/parawave \
  --test-command "uv run --extra dev --extra sqlite pytest tests/ -v --tb=short"
go-ship-it register-repo go-ship-it /path/to/go-ship-it \
  --feedback \
  --test-command "uv run pytest -q"
```

This creates `state/repos/parawave/` as the target repo and `state/repos/go-ship-it/` as the place for GoShipit product feedback discovered during ParaWave work.

Those folders are generated local state and are ignored by Git. Keep the committed source as the setup helper and docs; do not commit workspace-specific repo paths.

This creates the repo folder:

```text
state/repos/my-repo/
  repo.yaml
  context.md
  issues/
    todo/
    execution/
    archive/
```

Put durable repo-wide notes in `context.md`: setup gotchas, common commands, confusing conventions, and lessons that should apply across future issues.

## What Gets Created

Across the first issue flow, GoShipit should create only local, inspectable artifacts:

```text
state/repos/<repo>/issues/todo/<issue-id>/issue.md
state/repos/<repo>/issues/execution/<issue-id>/issue.md
state/repos/<repo>/issues/execution/<issue-id>/run.yaml
state/repos/<repo>/issues/execution/<issue-id>/notes.md
state/repos/<repo>/issues/execution/<issue-id>/handoff.md
state/repos/<repo>/issues/execution/<issue-id>/evidence.md
state/repos/<repo>/issues/execution/<issue-id>/pr.md
state/repos/<repo>/issues/execution/<issue-id>/logs/events.jsonl
state/repos/<repo>/issues/execution/<issue-id>/logs/commands/*.yaml
worktrees/<repo>/<issue-id>/.go-ship-it/context.yaml
```

`state/repos/<repo>/issues/execution/<issue-id>/run.yaml` is the active run metadata source of truth. `.go-ship-it/context.yaml` is only a worktree pointer back to that run and must match before current-run commands write notes or command records.

`evidence.md` appears after `export-run`. It is an optional issue-local snapshot for review and handoff. `pr.md` appears after `prepare-pr` and is the local PR preview. GoShipit maintainers also keep committed historical run reports under `docs/dogfood/`; normal user runs should not write there by default.

## Disposable Target Harness

For a repeatable local smoke test against any Git repo, use the generic target harness with explicit target values:

```bash
scripts/run-target-e2e.py \
  --target-id my-repo \
  --target-path /path/to/my-repo \
  --setup-command "uv sync" \
  --test-command "uv run pytest"
```

The harness clones the target into a temporary run root, registers that clone with isolated GoShipit state, drives the issue lifecycle through the CLI, and writes a Markdown report. It does not choose a default target repo.

### Contributor Fixture: Parawave

GoShipit contributors can use `scripts/dev/run-parawave-e2e.sh` inside this development workspace. ParaWave is a local fixture for GoShipit contributor testing; it is not a default target for users.

## Issue Flow

Use `skills/manage-issues/SKILL.md` for steps 1-4 (and the return-to-todo path in step 19). Use `skills/work-issue/SKILL.md` for steps 5-16. Use `skills/close-out/SKILL.md` for steps 17-19 (the prepare-pr/publish/archive path).

1. Initialize the control root with `go-ship-it init`, then register the target repo with `go-ship-it register-repo <repo> <local-path-or-git-url>`, or inspect an existing target with `go-ship-it show-repo <repo>`.
2. If every issue worktree needs local files or bootstrap work, configure `go-ship-it update-repo <repo> --worktree-setup-command "<command>"`. This automatic bootstrap command runs from each new issue worktree and records evidence under that issue's logs. Manual validation checks still use `run-check --check setup|test|lint`.
3. Add an issue with `go-ship-it add-issue`.
4. Start it with `go-ship-it start-issue <repo>/<issue-id>` (or `--quick` for a small fix that should skip straight to `implement`; promote it later with `go-ship-it set-track <repo>/<issue-id> standard --note "<why the issue grew>"` if it grows).
5. Inspect it with `go-ship-it show-issue <repo>/<issue-id>`.
6. Inspect the run with `go-ship-it show-run <repo>/<issue-id>`.
7. Confirm the worktree `.go-ship-it/context.yaml` matches the issue id and claim id.
8. From inside the managed worktree, use current-run detection for run-bound commands, for example `go-ship-it show-run` or the explicit `go-ship-it show-run --current`.
9. Record investigation evidence with `set-phase` and `append-note`.
10. Record proposal evidence before implementation.
11. Implement only inside the worktree shown by `show-issue`.
12. Run configured checks with `go-ship-it run-check --current --check test` from the worktree, or `go-ship-it run-check <repo>/<issue-id> --check test` from the control root.
13. Create an explicit resume snapshot with `go-ship-it handoff --write` from the worktree, or `go-ship-it handoff <repo>/<issue-id> --write` from the control root, when another session should continue.
14. Export issue-local evidence with `go-ship-it export-run`.
15. Ask an independent checker/sub-agent to review the issue problem, acceptance criteria, diff, notes, and command evidence. Record its verdict and caveats in the Review note.
16. Run `go-ship-it verify-run <repo>/<issue-id> --strict` and resolve or explicitly report every warning before cleanup.
17. Prepare a local PR preview with `go-ship-it prepare-pr <repo>/<issue-id> --branch <team-branch-name>`. The managed local branch is internal; this PR branch is chosen per issue and recorded in the run for later publish/rerun commands.
18. Publish with `go-ship-it publish-pr <repo>/<issue-id> --approved` only after approval, or omit `--approved` when `pull_request.auto_publish: true` is set for the repo. Either way, `publish-pr` also refuses to run while `verify-run` reports any error or warning — that gate is absolute and has no override; fix the evidence and rerun instead. Repos with `pull_request.provider: none` skip this step; the reviewed local `pr.md` is their final gate.
19. Cleanup to `archive` with `--confirm --remove-worktree` for completed work (archiving is terminal, so `--confirm` is required), or return to `todo` with `--remove-worktree` when work should be retried later. If the managed worktree has uncommitted target changes, cleanup refuses to remove it by default. Commit/prepare the PR, preserve the worktree for review, or use `--discard-worktree-changes` only when intentionally throwing local work away.
20. Run `go-ship-it doctor` again.

For agent-driven checks, prefer structured output:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <repo>/<issue-id> --json
```
