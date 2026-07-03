# GoShipit Command Surface

GoShipit has three surfaces.

## Agent Skill Surface

This is the surface coding agents should see first:

- `using-go-ship-it`: orient to package root, control root, state, and worktree boundaries.
- `manage-issues`: initialize/register, add todos, start issues, inspect status, and clean up active issues.
- `work-issue`: investigate, propose, implement, test, review, and record run evidence.

Avoid adding a new skill when the behavior is only a new CLI verb or a new reference note.

## CLI Surface

The CLI is plumbing for skills and humans. The normal path is:

```sh
go-ship-it init --repo-id <id> --repo-path <path> [--test-command <cmd>]
go-ship-it add-issue --repo <id> --title <title> --problem <problem>
go-ship-it start-issue <issue-id>
go-ship-it status
go-ship-it show-run <issue-id> --handoff
go-ship-it run-check <issue-id> --check test
go-ship-it handoff <issue-id> --write
go-ship-it export-run <issue-id> --output docs/dogfood/<issue-id>-evidence.md
go-ship-it verify-run <issue-id> --strict
go-ship-it cleanup-issue <issue-id> --destination archive --note <note> --remove-worktree
```

Advanced commands such as `show-run`, `handoff`, `append-note`, `append-log`, `set-phase`, `verify-run`, `export-run`, `doctor`, and `package-root` support the lifecycle but do not need separate skills.

When an agent needs structured output instead of Markdown, use:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <issue-id> --json
```

Use `go-ship-it verify-run <issue-id> --strict` as the pre-cleanup readiness gate. It should pass before normal archive cleanup unless the user explicitly accepts the remaining warnings.

Registered repos use a folder shape:

```text
state/repos/<repo>/
  repo.yaml
  context.md
```

Inside a managed issue worktree, run-bound commands can omit the issue id. `--current` is the explicit form:

```sh
go-ship-it status
go-ship-it show-run
go-ship-it show-run --current
go-ship-it append-note --current --section "Investigation" --note "<note>"
go-ship-it set-phase --current test --note "<ready>"
go-ship-it run-check --current --check test
go-ship-it handoff --write
```

Current-run detection reads `.go-ship-it/context.yaml` and verifies it against the run metadata before writing state.

## Maintainer Surface

Use `just` as the small release and maintenance wrapper:

```sh
just test
just doctor
just build
just package-acceptance
just agent-cli-check
just release-check
```

The source of truth remains the scripts and tests these recipes call.
