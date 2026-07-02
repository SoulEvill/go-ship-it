# Agent CLI Integration Validation

Date: 2026-07-02

## Results

- Confirmed Claude Code CLI is installed.
- Confirmed Claude plugin manifest validates in strict mode.
- Confirmed Claude accepts the GoShipit repo through session-local `--plugin-dir`.
- Installed Cursor Agent through the Cursor wrapper after approval and confirmed `cursor-agent` is available.
- Confirmed Cursor Agent accepts the GoShipit repo through session-local `--plugin-dir`.
- Confirmed Codex plugin command is available and `codex plugin list --json` returns JSON.
- Added cleanup-safe validation script and pytest coverage.

## Commands

```sh
claude plugin validate --strict .
# Validation passed

cursor agent --help
# Installed cursor-agent through the Cursor wrapper after approval

cursor-agent --plugin-dir . --help
# Accepted --plugin-dir and printed help

scripts/validate-agent-cli-integration.py --json
# Claude, Cursor Agent, Codex, and fallback installer checks passed or skipped by design

uv run pytest tests/test_agent_cli_integration.py -v
# 4 passed
```

## Cleanup Boundary

The automated validation does not install a persistent GoShipit plugin into Claude, Cursor, or Codex.

It uses:

- Claude session-local `--plugin-dir`
- Cursor Agent session-local `--plugin-dir`
- Codex read-only `plugin list --json`
- temporary fallback install targets that are removed automatically

If GoShipit later gets marketplace publication, persistent install/uninstall tests should be added separately and must preserve any pre-existing user install.

## Notes

- `cursor agent status` crashed while reading local account/keychain state, so the validator intentionally avoids authenticated Cursor Agent commands.
- Cursor Agent was not initially installed; the Cursor wrapper downloaded it after explicit approval.
- Codex local plugin install appears marketplace-based from the current help output, so local package loading is not validated there yet.

## Lessons To Promote

- Integration tests should validate package loading without mutating user plugin state.
- Session-local plugin loading is the right development path for Claude and Cursor.
- Persistent install/uninstall tests should be marketplace-specific and preserve any existing user-installed GoShipit plugin.

