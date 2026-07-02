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

Package metadata lives in:

- `.claude-plugin/plugin.json`
- `.codex-plugin/plugin.json`
- `.cursor-plugin/plugin.json`

Local fallback installers remain available for dogfood:

- Claude Code fallback: `scripts/install-claude-skills.sh`
- Cursor fallback: `scripts/install-cursor-adapter.sh`

See `docs/install.md`.

Validate local agent CLI package loading with:

```sh
scripts/validate-agent-cli-integration.py
```

Validate a built wheel in a fresh temporary install room with:

```sh
uv build
scripts/validate-packaged-install.py --wheel dist/go_ship_it-0.1.0-py3-none-any.whl
```

## User E2E Test

See `docs/user-e2e.md`.
