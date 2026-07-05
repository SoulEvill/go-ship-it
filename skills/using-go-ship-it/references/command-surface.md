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
go-ship-it init --repo-id <id> --repo-source <local-path-or-git-url> [--test-command <cmd>]
go-ship-it update-repo <id> --worktree-setup-command <cmd>
go-ship-it add-issue --repo <id> --title <title> --problem <problem>
go-ship-it start-issue <repo>/<issue-id>
go-ship-it status
go-ship-it show-run <repo>/<issue-id> --handoff
go-ship-it run-check <repo>/<issue-id> --check test
go-ship-it handoff <repo>/<issue-id> --write
go-ship-it export-run <repo>/<issue-id>
go-ship-it verify-run <repo>/<issue-id> --strict
go-ship-it prepare-pr <repo>/<issue-id> --branch <team-branch-name>
go-ship-it cleanup-issue <repo>/<issue-id> --destination archive --note <note> --remove-worktree
```

`export-run` defaults to `evidence.md` inside the issue folder. Use `--output` only when the user explicitly wants a copy somewhere else.

`prepare-pr` is local-only and writes `pr.md` inside the issue folder. `publish-pr` pushes the local work branch to the recorded PR branch and runs `gh pr create`; use it only after approval unless the repo allows auto publish.

For GoShipit dogfood or self-improvement, setup can also register `go-ship-it` as the product-feedback repo:

```sh
go-ship-it init \
  --repo-id <target-repo> \
  --repo-source <target-path-or-git-url> \
  --test-command <target-test-command> \
  --feedback-repo-source <go-ship-it-repo-path-or-git-url> \
  --feedback-test-command "uv run pytest -q"
```

In the GoShipit development workspace, use `scripts/setup/parawave.sh` to register `parawave` as the dogfood target repo and `go-ship-it` as the feedback repo.

Advanced commands such as `show-run`, `handoff`, `append-note`, `set-phase`, `verify-run`, `export-run`, `doctor`, and `package-root` support the lifecycle but do not need separate skills.

When an agent needs structured output instead of Markdown, use:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <repo>/<issue-id> --json
```

Use `go-ship-it verify-run <repo>/<issue-id> --strict` as the pre-cleanup readiness gate. It should pass before normal archive cleanup unless the user explicitly accepts the remaining warnings.

Registered repos use a folder shape:

```text
state/repos/<repo>/
  repo.yaml
  context.md
  issues/
    todo/<issue-id>/issue.md
    execution/<issue-id>/
      issue.md
      run.yaml
      notes.md
      handoff.md
      evidence.md
      pr.md
      logs/
        events.jsonl
        commands/*.yaml
    archive/<issue-id>/issue.md
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

Repo sources may be local paths or Git URLs. URL sources are cloned into `worktrees/<repo>/_source`; active issue worktrees are siblings such as `worktrees/<repo>/issue-001`. Do not edit `_source` during issue work.

Optional worktree setup lives in `state/repos/<repo>/repo.yaml` under `worktree_setup.command`. It runs from each new issue worktree after `start-issue` creates it and records command evidence under that issue's `logs/commands/` folder.

Repo-level PR config lives in `state/repos/<repo>/repo.yaml`:

```yaml
pull_request:
  provider: github
  remote: origin
  auto_publish: false
```

The local work branch remains GoShipit-owned. The PR branch is an issue-level decision: supply it with `prepare-pr --branch <branch>` the first time, and later PR commands can reuse the branch recorded in that run.

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
