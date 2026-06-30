# User E2E Checklist

Run this before trying GitHub, PR, or Jira integrations.

## Preflight

```sh
go-ship-it doctor
go-ship-it status
```

## Issue Flow

1. Register or inspect the target repo with `go-ship-it show-repo <repo>`.
2. Add an issue with `go-ship-it add-issue`.
3. Start it with `go-ship-it start-issue <issue-id>`.
4. Inspect it with `go-ship-it show-issue <issue-id>`.
5. Inspect the run with `go-ship-it show-run <issue-id>`.
6. Record investigation evidence with `set-phase` and `append-note`.
7. Record proposal evidence before implementation.
8. Implement only inside the worktree shown by `show-issue`.
9. Run configured checks with `go-ship-it run-check`.
10. Export evidence with `go-ship-it export-run`.
11. Cleanup to `archive` or return to `todo`.
12. Run `go-ship-it doctor` again.
