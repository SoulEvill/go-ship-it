# GoShipit

GoShipit is a local-first control repo for agent-assisted software work.

## Lifecycle

```text
todo -> execution -> archive
```

Inside `execution`, detailed phase progress follows a strict enum, tracked as run metadata and authored notes:

```text
setup -> investigate -> propose -> implement -> review -> prepare-pr -> publish -> archived
```

Every issue also has a `track`. `standard` walks the full enum with Investigation, Proposal, Implementation, and Review notes. `quick` (`start-issue --quick`) starts directly at `implement` with only Implementation and Review notes, and can be promoted mid-flight with `set-track <repo>/<issue-id> standard` if the fix grows beyond a quick change.

Shipping a reviewed issue is three separate gates, crossed in order and never bundled: `prepare-pr` (reversible, local PR preview), `publish` (irreversible: pushes and opens a PR, blocked while `verify-run` reports any finding), and `archive` (terminal: `cleanup-issue --destination archive` requires `--confirm`).

## Development

```sh
uv sync
uv run pytest -v
uv run go-ship-it --help
```

## Local Install From A Clone

```sh
uv tool install .
go-ship-it --help
go-ship-it package-root
```

`go-ship-it package-root` prints the bundled agent package directory. Use that path when an agent CLI asks for a local plugin/package directory.

## First Health Check

```sh
go-ship-it doctor
go-ship-it status
```

Agent sessions should run lifecycle commands from the GoShipit control root, or pass `--root <control-root>` explicitly. The control root contains `state/` and `worktrees/`. The package root contains skills and hooks. Target repo edits belong only inside the active issue worktree.

In a clone-based development checkout, use `uv run go-ship-it ...` when the CLI has not been installed on PATH. In an installed package, use `go-ship-it ...`.

## Normal Path

The first-run command surface is intentionally small:

```sh
go-ship-it init
go-ship-it register-repo my-repo /path/to/repo --test-command "uv run pytest"
# or:
go-ship-it register-repo my-repo https://github.com/org/repo.git --test-command "uv run pytest"
go-ship-it add-issue --repo my-repo --title "Fix parser" --problem "Parser drops quoted values."
go-ship-it start-issue my-repo/issue-001
# or, for a small fix that skips investigate/propose: go-ship-it start-issue my-repo/issue-001 --quick
go-ship-it status
go-ship-it show-run my-repo/issue-001 --handoff
go-ship-it run-check my-repo/issue-001 --check test
go-ship-it handoff my-repo/issue-001 --write
go-ship-it export-run my-repo/issue-001
go-ship-it verify-run my-repo/issue-001 --strict
go-ship-it prepare-pr my-repo/issue-001 --branch feature/fix-parser
go-ship-it publish-pr my-repo/issue-001 --approved
go-ship-it cleanup-issue my-repo/issue-001 --destination archive --confirm --note "Done." --remove-worktree
```

Repos default to `pull_request.provider: github`, so the reviewed local `pr.md` is published with `publish-pr --approved` before archiving. Only `provider: none` repos skip publish and go straight from `prepare-pr` to `cleanup-issue --destination archive`; the signed-off local `pr.md` is their final gate.

A `quick`-track issue that grows beyond a small fix can be promoted to the full lifecycle: `go-ship-it set-track my-repo/issue-001 standard --note "<why the issue grew>"`.

`export-run` writes `evidence.md` inside the issue folder by default. `docs/dogfood/` is only for committed GoShipit maintainer run reports, not normal user runs.

`cleanup-issue --remove-worktree` refuses to delete a dirty managed worktree by default. Commit or prepare the PR first, preserve the worktree, or use `--discard-worktree-changes` only when intentionally throwing local target work away.

When the control root is being used to improve GoShipit itself, setup can also register the GoShipit repo as the product-feedback target:

```sh
go-ship-it init
go-ship-it register-repo my-repo /path/to/my-repo --test-command "uv run pytest"
go-ship-it register-repo go-ship-it /path/to/go-ship-it --feedback --test-command "uv run pytest -q"
```

That creates `state/repos/go-ship-it/` with product-feedback context so GoShipit friction from target-repo work can become normal `go-ship-it/<issue-id>` issues.

For contributor testing against the sibling ParaWave repo, use the helper instead:

```sh
scripts/setup/parawave.sh
```

It registers `state/repos/parawave/` as the target repo and `state/repos/go-ship-it/` as the feedback repo.

Those repo registrations are generated local state and are intentionally ignored by Git. The committed source of truth is the helper and docs, not this workspace's absolute paths.

Use `status` as the command center. It shows the control root, package root, current branch, active issues, worktrees, and useful next commands.

Each registered repo gets its own visible state folder:

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
      logs/
        events.jsonl
        commands/*.yaml
    archive/<issue-id>/issue.md
```

`repo.yaml` is the machine-readable config. `context.md` is the repo-level background file for conventions, commands, and gotchas that should apply across issues. Issue ids are repo-local, so explicit issue references use `<repo>/<issue-id>`.

Repo sources can be local paths or Git URLs. Local sources are recorded directly. Git URL sources are cloned into the repo's managed worktree bucket:

```text
worktrees/<repo>/_source
worktrees/<repo>/<issue-id>
```

The `_source` checkout is the canonical local clone GoShipit uses to create isolated issue worktrees. Target repo edits still belong only inside the active issue worktree, not `_source`.

GoShipit does not currently auto-refresh registered sources before starting work. A Git URL source uses the local `_source` clone created at registration time; a local source uses the user's local checkout. If starting from the latest upstream state matters, refresh the registered source before starting the issue.

Some repos need local files or generated setup that Git worktrees do not copy, such as `.env`, private config, local fixtures, or dependency bootstrapping. Configure one optional automatic bootstrap script to run after every issue worktree is created:

```sh
go-ship-it update-repo my-repo --worktree-setup-command "state/repos/my-repo/setup/setup-worktree.sh"
```

The command runs from the new issue worktree. GoShipit records stdout, stderr, and exit code under that issue's `logs/commands/` folder. If the command fails, the issue remains active in setup phase so the failure can be inspected.

This is separate from repo check commands such as `setup_command`, `test_command`, and `lint_command`. Those are manual validation checks invoked with `run-check --check setup|test|lint`.

Repo PR behavior also lives in `repo.yaml`:

```yaml
pull_request:
  provider: github
  remote: origin
  auto_publish: false
```

The managed local work branch remains GoShipit-owned, for example `go-ship-it/issue-001`. The PR branch is separate and is chosen per issue when preparing the PR. Use `prepare-pr --branch <team-branch-name>` the first time; GoShipit records that branch in the issue run and reuses it on later PR preview or publish commands.

`start-issue` creates a deterministic claim id and writes `.go-ship-it/context.yaml` inside the managed worktree so parallel sessions can anchor themselves to the right issue/run. From inside that worktree, run-bound commands can omit the issue id; `--current` is the explicit form when you want to make that intent visible:

```sh
go-ship-it status
go-ship-it show-run
go-ship-it show-run --current
go-ship-it append-note --current --section "Investigation" --for-phase investigate --note "Read parser tests."
go-ship-it run-check --current --check test
go-ship-it handoff --write
```

The context file is only a pointer. GoShipit verifies it against `state/repos/<repo>/issues/execution/<issue-id>/run.yaml` before writing notes or command records, which prevents a stale or copied worktree context from silently targeting the wrong run. `handoff --write` creates `state/repos/<repo>/issues/execution/<issue-id>/handoff.md` when the user wants a future session to resume with enough context.

## What Gets Created

Across a first issue flow, GoShipit creates visible local artifacts:

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

`evidence.md` appears after `export-run`; `handoff.md` appears after `handoff --write`; `pr.md` appears after `prepare-pr`.

Before cleanup, run the readiness gate:

```sh
go-ship-it status
go-ship-it handoff <repo>/<issue-id> --write
go-ship-it export-run <repo>/<issue-id>
go-ship-it verify-run <repo>/<issue-id> --strict
go-ship-it prepare-pr <repo>/<issue-id> --branch <team-branch-name>
```

`prepare-pr` is local-only. It writes `pr.md` for review and records the issue-level PR branch in `run.yaml`. `publish-pr` is the native GitHub path: it pushes the local work branch to the recorded PR branch, then runs `gh pr create --body-file pr.md`. When `pull_request.auto_publish` is false, `publish-pr` requires `--approved`. Either way, `publish-pr` additionally refuses to run while `verify-run` reports any error or warning — this check is absolute and has no override flag; fix the evidence and rerun instead. Repos with `pull_request.provider: none` never publish: the reviewed local `pr.md` from `prepare-pr` is their final gate before archive.

Before cleanup, agents should use a native sub-agent/reviewer/checker when available to judge whether the issue problem and acceptance criteria are actually satisfied by the diff, notes, and command evidence. Record that verdict in the Review note.

`verify-run --strict` fails on warnings, including missing acceptance criteria evidence or missing handoff context. Agents can use structured output when they should not scrape Markdown:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <repo>/<issue-id> --json
```

`notes.md` is for human or agent-authored investigation, proposal, implementation, and review notes. `logs/` is for program-generated records only. GoShipit product feedback should be added as a normal issue under the `go-ship-it` repo and linked back to the source repo/issue/run where it was observed.

## Agent Tool Setup

GoShipit skills are bundled as one package per agent harness. Install the CLI/package once, then point each agent harness at the package root:

```sh
claude --plugin-dir "$(go-ship-it package-root)" --help
cursor-agent --plugin-dir "$(go-ship-it package-root)" --help
```

The agent-facing skill surface is intentionally small:

- `using-go-ship-it`: orient to package root, control root, state, and worktree boundaries.
- `manage-issues`: initialize/register, add todos, start issues, inspect status, and clean up.
- `work-issue`: investigate, propose, implement, review, and record run evidence.
- `close-out`: ship a reviewed issue through the three gates — prepare the local PR, publish it, archive the issue.

The CLI has more commands because it is plumbing for these skills.

Package metadata lives in:

- `.claude-plugin/plugin.json`
- `.codex-plugin/plugin.json`
- `.cursor-plugin/plugin.json`

Local fallback installers remain available for development:

- Claude Code fallback: `scripts/install-claude-skills.sh`
- Cursor fallback: `scripts/install-cursor-adapter.sh`

See `docs/install.md`.

For maintainers, `docs/maintainers.md` captures the command surface, state shape, and when to add CLI plumbing versus new skills.

Validate local agent CLI package loading with:

```sh
scripts/validate-agent-cli-integration.py
```

Validate a built wheel in a fresh temporary install room with:

```sh
uv build
scripts/validate-packaged-install.py --wheel dist/go_ship_it-0.1.0-py3-none-any.whl
```

Run the lightweight release gate with:

```sh
scripts/release-check.py
```

If `just` is installed, the same gate is available as:

```sh
just release-check
```

## User E2E Test

See `docs/user-e2e.md`.
