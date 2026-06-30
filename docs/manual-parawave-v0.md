# Manual Parawave V0 Validation

Run these commands from the `go-ship-it` repo.

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

Expected: a new issue file path is printed, such as `state/issues/todo/<issue-id>.md`.
Copy the issue id from that path for the next commands.

## 3. Start the issue

```sh
uv run go-ship-it start-issue <issue-id> --claimed-by manual-validation
```

Expected:

- `state/issues/execution/<issue-id>.md` exists.
- `state/runs/<issue-id>/run.yaml` exists.
- `worktrees/parawave/<issue-id>/` exists.

## 4. Return the issue to todo

```sh
uv run go-ship-it cleanup-issue <issue-id> --destination todo --note "Manual validation complete." --remove-worktree
```

Expected:

- `state/issues/todo/<issue-id>.md` exists again.
- `state/issues/execution/<issue-id>.md` no longer exists.
