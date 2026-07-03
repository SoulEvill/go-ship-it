# GoShipit

GoShipit is a local-first control repo for agent-assisted software work.

## Lifecycle

```text
todo -> execution -> archive
```

Detailed phase progress is tracked as metadata and journal evidence:

```text
setup -> investigate -> propose -> implement -> test -> cleanup
```

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

## Normal Path

The first-run command surface is intentionally small:

```sh
go-ship-it init --repo-id my-repo --repo-path /path/to/repo --test-command "uv run pytest"
go-ship-it add-issue --repo my-repo --title "Fix parser" --problem "Parser drops quoted values."
go-ship-it start-issue issue-001
go-ship-it status
go-ship-it show-run issue-001 --handoff
go-ship-it run-check issue-001 --check test
go-ship-it handoff issue-001 --write
go-ship-it cleanup-issue issue-001 --destination archive --note "Done."
```

Use `status` as the command center. It shows the control root, package root, current branch, active issues, worktrees, and useful next commands.

Each registered repo gets its own visible folder:

```text
state/repos/<repo>/
  repo.yaml
  context.md
```

`repo.yaml` is the machine-readable config. `context.md` is the repo-level background file for conventions, commands, and gotchas that should apply across issues.

`start-issue` creates a deterministic claim id and writes `.go-ship-it/context.yaml` inside the managed worktree so parallel sessions can anchor themselves to the right issue/run. From inside that worktree, run-bound commands can omit the issue id; `--current` is the explicit form when you want to make that intent visible:

```sh
go-ship-it status
go-ship-it show-run
go-ship-it show-run --current
go-ship-it append-note --current --section "Investigation" --phase investigate --note "Read parser tests."
go-ship-it run-check --current --check test
go-ship-it handoff --write
```

The context file is only a pointer. GoShipit verifies it against `state/runs/<issue-id>/run.yaml` before writing evidence, which prevents a stale or copied worktree context from silently targeting the wrong run. `handoff --write` creates `state/runs/<issue-id>/handoff.md` when the user wants a future session to resume with enough context.

## Run Comments

Use run logs for lightweight process observations and raw-data pointers:

```sh
go-ship-it append-log issue-001 --note "Agent recovered with --root." --source transcript:/path/to/session.jsonl
go-ship-it show-run issue-001 --logs
```

Run logs are comments, not a fixed lesson taxonomy.

## Agent Tool Setup

GoShipit skills are bundled as one package per agent harness. Install the CLI/package once, then point each agent harness at the package root:

```sh
claude --plugin-dir "$(go-ship-it package-root)" --help
cursor-agent --plugin-dir "$(go-ship-it package-root)" --help
```

The agent-facing skill surface is intentionally small:

- `using-go-ship-it`: orient to package root, control root, state, and worktree boundaries.
- `manage-issues`: initialize/register, add todos, start issues, inspect status, and clean up.
- `work-issue`: investigate, propose, implement, test, review, and record run evidence.

The CLI has more commands because it is plumbing for these skills.

Package metadata lives in:

- `.claude-plugin/plugin.json`
- `.codex-plugin/plugin.json`
- `.cursor-plugin/plugin.json`

Local fallback installers remain available for dogfood:

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
