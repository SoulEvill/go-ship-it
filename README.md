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
```

## First Health Check

```sh
go-ship-it doctor
go-ship-it status
```

Agent sessions should run these from the GoShipit control repo root, or pass `--root <control-root>` explicitly. Target repo edits belong only inside the active issue worktree.

## Agent Tool Setup

GoShipit skills are bundled as one package per agent harness. Install the package separately for Claude Code, Codex, Cursor, or any other agent tool you use.

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

## User E2E Test

See `docs/user-e2e.md`.
