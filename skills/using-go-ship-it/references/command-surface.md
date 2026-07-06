# GoShipit Command Surface

GoShipit has three surfaces.

## Agent Skill Surface

This is the surface coding agents should see first:

- `using-go-ship-it`: orient to package root, control root, state, and worktree boundaries.
- `manage-issues`: initialize/register, add todos, start issues, inspect status, and clean up active issues.
- `work-issue`: investigate, propose, implement, review, and record run evidence.
- `close-out`: ship a reviewed issue — prepare the local PR, publish it, archive the issue.

Avoid adding a new skill when the behavior is only a new CLI verb or a new reference note.

## CLI Surface

The CLI is plumbing for skills and humans. Phase is a strict enum: `setup -> investigate -> propose -> implement -> review -> prepare-pr -> publish -> archived`. Track is `standard` (full enum, four note sections) or `quick` (starts at `implement`, two note sections); set it at start or promote it later with `start-issue --quick` / `set-track`.

The normal path is:

```sh
go-ship-it init
go-ship-it register-repo <id> <local-path-or-git-url> [--test-command <cmd>]
go-ship-it update-repo <id> --worktree-setup-command <cmd>
go-ship-it add-issue --repo <id> --title <title> --problem <problem>
go-ship-it start-issue <repo>/<issue-id>
go-ship-it start-issue <repo>/<issue-id> --quick
go-ship-it set-track <repo>/<issue-id> standard --note <note>
go-ship-it status
go-ship-it show-run <repo>/<issue-id> --handoff
go-ship-it set-phase <repo>/<issue-id> implement --inner-loop tdd --note <note>
go-ship-it set-phase <repo>/<issue-id> review --review-pipeline plugin:<name> --note <note>
go-ship-it run-check <repo>/<issue-id> --check test
go-ship-it handoff <repo>/<issue-id> --write
go-ship-it export-run <repo>/<issue-id>
go-ship-it verify-run <repo>/<issue-id> --strict
go-ship-it prepare-pr <repo>/<issue-id> --branch <team-branch-name>
go-ship-it cleanup-issue <repo>/<issue-id> --destination archive --confirm --note <note> --remove-worktree
```

`start-issue --quick` is shorthand for `--track quick`; `set-track` promotes a `quick` issue to `standard` mid-flight (only forward, never demoted). `set-phase --inner-loop` records the implement loop (`tdd`, `debug`, `spike`, or `none`; `none` requires `--inner-loop-reason`); `set-phase --review-pipeline` records how review was run (`self`, `clean-room`, or `plugin:<name>`).

`export-run` defaults to `evidence.md` inside the issue folder. Use `--output` only when the user explicitly wants a copy somewhere else.

`prepare-pr` is local-only and writes `pr.md` inside the issue folder. `publish-pr` pushes the local work branch to the recorded PR branch and runs `gh pr create`; when repo auto-publish is disabled, use `publish-pr --approved` only after the user approves publishing. Independent of `--approved`/`auto_publish`, `publish-pr` also refuses to run while `verify-run` reports any error or warning — that gate is absolute, with no override flag. Repos with `pull_request.provider: none` skip publish entirely; the reviewed local `pr.md` is their final gate before archive.

`cleanup-issue --remove-worktree` refuses to delete a dirty managed worktree by default. Preserve the worktree, commit/prepare PR first, or use `--discard-worktree-changes` only when the user explicitly chooses to discard local target work. `cleanup-issue --destination archive` also requires `--confirm`, acknowledging that archive is terminal (no reopen/unarchive).

When the control root is being used to improve GoShipit itself, setup can also register `go-ship-it` as the product-feedback repo:

```sh
go-ship-it init
go-ship-it register-repo <target-repo> <target-path-or-git-url> --test-command <target-test-command>
go-ship-it register-repo go-ship-it <go-ship-it-repo-path-or-git-url> --feedback --test-command "uv run pytest -q"
```

If the user explicitly asks to set up ParaWave in the GoShipit development workspace, use `scripts/setup/parawave.sh`. It registers `parawave` as a normal target repo and `go-ship-it` as the feedback repo.

Advanced commands such as `show-run`, `handoff`, `append-note`, `set-phase`, `set-track`, `verify-run`, `export-run`, `doctor`, and `package-root` support the lifecycle but do not need separate skills.

When an agent needs structured output instead of Markdown, use:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <repo>/<issue-id> --json
```

Use `go-ship-it verify-run <repo>/<issue-id> --strict` as the pre-cleanup readiness gate. It should pass before normal archive cleanup unless the user explicitly accepts the remaining warnings.

Use the agent platform's native sub-agent, reviewer, or checker mechanism for semantic done/not-done review before cleanup when available. Record that judgment in the Review note; keep `verify-run --strict` as the deterministic evidence-structure gate.

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
go-ship-it set-phase --current review --note "<ready for review>"
go-ship-it run-check --current --check test
go-ship-it handoff --write
```

Current-run detection reads `.go-ship-it/context.yaml` and verifies it against the run metadata before writing state.

Repo sources may be local paths or Git URLs. URL sources are cloned into `worktrees/<repo>/_source`; active issue worktrees are siblings such as `worktrees/<repo>/issue-001`. Do not edit `_source` during issue work.

GoShipit does not currently auto-refresh registered sources. Git URL sources use the local `_source` clone created at registration time; local-path sources use the user's local checkout. If upstream freshness matters, refresh the source before starting a new issue.

Optional worktree setup lives in `state/repos/<repo>/repo.yaml` under `worktree_setup.command`. It is automatic bootstrap: it runs from each new issue worktree after `start-issue` creates it and records command evidence under that issue's `logs/commands/` folder. Manual validation commands live in `setup_command`, `test_command`, and `lint_command`, and are invoked with `run-check`.

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
