# Install GoShipit

GoShipit has two install surfaces:

- the `go-ship-it` CLI
- the bundled agent skill package

Install the CLI once for the control repo. Install the skill package separately for each agent harness you use.

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

## Skill Package Model

GoShipit skills are distributed as one package, not as independent skill installs.

The package contains:

- `.claude-plugin/plugin.json`
- `.codex-plugin/plugin.json`
- `.cursor-plugin/plugin.json`
- `hooks/`
- `skills/`
- `references/`

Each harness has its own plugin installation mechanism, so install GoShipit separately in Claude Code, Codex, Cursor, or any other agent tool.

## Claude Code

Use the GoShipit plugin package when local plugin installation is available in your Claude Code setup. The package root is the GoShipit repo.

Development fallback:

```sh
scripts/install-claude-skills.sh
```

The fallback copies skill folders into `.claude/skills/`. It is useful for local dogfood, but the package model is preferred because it keeps skills, hooks, and metadata versioned together.

## Codex

Use the Codex plugin package metadata in `.codex-plugin/plugin.json`.

After installing the package in Codex, start a session from the GoShipit repo and ask:

```text
I want to work on a GoShipit issue.
```

The session should orient to `using-go-ship-it`, `go-ship-it status`, and `go-ship-it doctor`.

## Clean Session Acceptance

For any harness, the first reliability check is working-directory safety. The session should either start from the GoShipit control repo root or pass that path explicitly:

```sh
go-ship-it --root <control-root> status
go-ship-it --root <control-root> doctor
```

The control root should contain `pyproject.toml`, `skills/using-go-ship-it/SKILL.md`, `state/`, and `worktrees/`.

If a session is accidentally in a target repo or target worktree, `go-ship-it status` should fail instead of showing an empty-looking workspace.

## Cursor

Use the Cursor plugin package metadata in `.cursor-plugin/plugin.json`. Cursor should load the shared `skills/` folder and session-start hook configuration.

Development fallback:

```sh
scripts/install-cursor-adapter.sh
```

The fallback writes `.cursor/rules/go-ship-it.mdc` and `AGENTS.md` so Cursor can orient to the canonical skill folders.

## Package Health Check

Run:

```sh
go-ship-it doctor
```

`doctor` reports lifecycle state issues and package health warnings, including missing manifests, missing bootstrap skill, and missing hook files.

## Agent CLI Validation

Run this before trying a live agent session:

```sh
scripts/validate-agent-cli-integration.py
```

This validates the local package against installed agent CLIs without creating persistent plugin installs:

- Claude Code: validates `.claude-plugin/plugin.json` and checks `claude --plugin-dir <repo>`.
- Cursor Agent: checks `cursor-agent --plugin-dir <repo>`.
- Codex: checks that `codex plugin list --json` is available.
- Fallback installers: copies Claude skills and Cursor adapter files into temporary directories that are removed automatically.

Persistent install/uninstall is intentionally not exercised here. Claude and Cursor both support session-local `--plugin-dir` loading, which is safer for local development. Marketplace-based installs should get their own test once GoShipit is published through a marketplace.

## Remote Integrations

GitHub, PR creation, Jira, and other remote services are intentionally not part of the first install path. Add them only after local e2e passes.
