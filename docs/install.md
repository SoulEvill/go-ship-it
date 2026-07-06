# Install GoShipit

GoShipit has two install surfaces:

- the `go-ship-it` CLI
- the bundled agent skill package

Install GoShipit once. The CLI exposes the bundled agent package root, and each agent harness can load that one package. Users should not install each skill independently.

## Development Install

```sh
uv sync
uv run go-ship-it --help
uv run pytest -v
```

In development, prefer `uv run go-ship-it ...` unless you have installed the CLI on PATH. In an installed package, use `go-ship-it ...`.

Optional convenience commands are available through `Justfile` when `just` is installed:

```sh
just test
just doctor
just release-check
```

## Local CLI Install

From the GoShipit clone:

```sh
uv tool install .
go-ship-it --help
go-ship-it package-root
```

`go-ship-it package-root` prints the directory that contains the bundled skills, hooks, manifests, references, and docs.

## Skill Package Model

GoShipit skills are distributed as one package, not as independent skill installs.

The package exposes four agent-facing skills:

- `using-go-ship-it`: session orientation and root/worktree boundaries.
- `manage-issues`: repo setup, issue creation, start/status, and cleanup.
- `work-issue`: investigation, proposal, implementation, and review, plus evidence capture.
- `close-out`: shipping a reviewed issue — prepare the local PR, publish it, archive the issue.

The package contains:

- `.claude-plugin/plugin.json`
- `.codex-plugin/plugin.json`
- `.cursor-plugin/plugin.json`
- `hooks/`
- `skills/`
- `references/`

Each harness has its own plugin installation mechanism, so install GoShipit separately in Claude Code, Codex, Cursor, or any other agent tool.

There are two roots:

- Package root: printed by `go-ship-it package-root`; contains `skills/`, `hooks/`, and plugin manifests.
- Control root: the workspace where lifecycle state lives; contains `state/` and `worktrees/`.

In clone-based development those roots may be the same directory. In package-install mode they are usually different.

## Claude Code

Use the GoShipit plugin package when local plugin installation is available in your Claude Code setup:

```sh
claude --plugin-dir "$(go-ship-it package-root)" --help
```

Development fallback:

```sh
scripts/install-claude-skills.sh
```

The fallback copies skill folders into `.claude/skills/`. It is useful for local development, but the package model is preferred because it keeps skills, hooks, and metadata versioned together.

## Codex

Use the Codex plugin package metadata in `.codex-plugin/plugin.json`.

After installing the package in Codex, start a session from a GoShipit control root and ask:

```text
I want to work on a GoShipit issue.
```

The session should orient to `using-go-ship-it`, `go-ship-it status`, and `go-ship-it doctor`.

If the session says `go-ship-it: command not found` in a clone-based development checkout, it should retry with `uv run go-ship-it` from the control root before reporting a setup failure.

## Clean Session Acceptance

For any harness, the first reliability check is working-directory safety. The session should either start from the GoShipit control repo root or pass that path explicitly:

```sh
go-ship-it --root <control-root> status
go-ship-it --root <control-root> doctor
```

The control root should contain `state/` and `worktrees/`. The package root should contain `skills/using-go-ship-it/SKILL.md`, `skills/manage-issues/SKILL.md`, `skills/work-issue/SKILL.md`, `skills/close-out/SKILL.md`, plugin manifests, and hooks.

If a session is accidentally in a target repo or target worktree, `go-ship-it status` should fail instead of showing an empty-looking workspace.

For a live agent session, a good first prompt is:

```text
Use GoShipit for this project. Start by orienting to the control root, show me status and doctor results, and do not edit the target repo until an active issue worktree is confirmed.
```

The agent should be able to use structured output if needed:

```sh
go-ship-it status --json
go-ship-it doctor --json
go-ship-it verify-run <repo>/<issue-id> --json
```

Before cleanup, the agent should run or recommend:

```sh
go-ship-it handoff <repo>/<issue-id> --write
go-ship-it export-run <repo>/<issue-id>
go-ship-it verify-run <repo>/<issue-id> --strict
```

## Cursor

Use the Cursor plugin package metadata in `.cursor-plugin/plugin.json`. Cursor should load the shared `skills/` folder and session-start hook configuration:

```sh
cursor-agent --plugin-dir "$(go-ship-it package-root)" --help
```

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

For a complete local release gate, run:

```sh
scripts/release-check.py
```

or, if `just` is installed:

```sh
just release-check
```

## Packaged Install Acceptance

Run this after building a wheel and before trying a live user session:

```sh
uv build
scripts/validate-packaged-install.py --wheel dist/go_ship_it-0.1.0-py3-none-any.whl
```

This creates a temporary fresh room, installs the wheel into a new virtual environment, runs `go-ship-it package-root`, initializes a temporary control root, registers a disposable target repo, and runs `go-ship-it doctor`, then checks whether Claude Code and Cursor Agent can load the installed package root when those CLIs are available.

It also drives a disposable first-issue flow: create a target git repo, register it, add and start an issue, inspect `status --json`, record evidence, run the configured test check, write handoff, export evidence, run `verify-run --strict`, archive with `--confirm --remove-worktree`, and run final `doctor`.

## Agent CLI Validation

Run this before trying a live agent session:

```sh
cd "$(go-ship-it package-root)"
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
