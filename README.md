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

## Agent Tool Setup

- Claude Code: `scripts/install-claude-skills.sh`
- Cursor: `scripts/install-cursor-adapter.sh`

See `docs/install.md`.

## User E2E Test

See `docs/user-e2e.md`.
