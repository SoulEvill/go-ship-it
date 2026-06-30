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
  --acceptance "A worktree is created under worktrees/parawave/issue-001."
```

Expected: `state/issues/todo/issue-001.md` is created.

## 3. Start the issue

```sh
uv run go-ship-it start-issue issue-001 --claimed-by manual-validation
```

Expected:

- `state/issues/execution/issue-001.md` exists.
- `state/runs/issue-001/run.yaml` exists.
- `worktrees/parawave/issue-001/` exists.

## 4. Return the issue to todo

```sh
uv run go-ship-it cleanup-issue issue-001 --destination todo --note "Manual validation complete." --remove-worktree
```

Expected:

- `state/issues/todo/issue-001.md` exists again.
- `state/issues/execution/issue-001.md` no longer exists.
