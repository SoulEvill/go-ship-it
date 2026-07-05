# Manual Parawave V0 Validation

Run these commands from the `go-ship-it` repo.

## 0. Register Parawave

```sh
scripts/dev/setup-parawave-dogfood.sh
```

Expected:

- `state/repos/parawave/repo.yaml` points to the ParaWave clone.
- `state/repos/parawave/context.md` exists for ParaWave repo-level notes.
- `state/repos/go-ship-it/context.md` exists for GoShipit product feedback found during dogfood runs.

## 1. Verify package tests

```sh
uv run pytest
```

Expected: all tests pass.

## 2. Add a sample issue

```sh
uv run go-ship-it add-issue \
  --repo parawave \
  --title "Manual validation issue" \
  --problem "Confirm GoShipit can create and start an issue against Parawave." \
  --context "This is a local smoke test." \
  --acceptance "A worktree is created for the printed issue id."
```

Expected: a new issue file path is printed, such as `state/repos/parawave/issues/todo/<issue-id>/issue.md`.
Copy the issue id from that path for the next commands.

## 3. Start the issue

```sh
uv run go-ship-it start-issue parawave/<issue-id> --claimed-by manual-validation
```

Expected:

- `state/repos/parawave/issues/execution/<issue-id>/issue.md` exists.
- `state/repos/parawave/issues/execution/<issue-id>/run.yaml` exists.
- `worktrees/parawave/<issue-id>/` exists.

## 4. Return the issue to todo

```sh
uv run go-ship-it cleanup-issue parawave/<issue-id> --destination todo --note "Manual validation complete." --remove-worktree
```

Expected:

- `state/repos/parawave/issues/todo/<issue-id>/issue.md` exists again.
- `state/repos/parawave/issues/execution/<issue-id>/` no longer exists.
