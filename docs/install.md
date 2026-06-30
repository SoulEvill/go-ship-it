# Install GoShipit

## Development Install

```sh
uv sync
uv run go-ship-it --help
uv run pytest -v
```

## Local CLI Install

From the GoShipit clone:

```sh
uv tool install .
go-ship-it --help
```

## Claude Code Project Skills

```sh
scripts/install-claude-skills.sh
```

This writes copies to `.claude/skills/` in the GoShipit clone. Start Claude Code from the GoShipit repo and invoke skills by folder name, for example `/add-issue` or `/start-issue`.

## Cursor Adapter

```sh
scripts/install-cursor-adapter.sh
```

This writes `.cursor/rules/go-ship-it.mdc` and `AGENTS.md`. Cursor should use those files to orient to GoShipit and read the canonical skill folders under `skills/`.

## Remote Integrations

GitHub, PR creation, Jira, and other remote services are intentionally not part of the first install path. Add them only after local e2e passes.
