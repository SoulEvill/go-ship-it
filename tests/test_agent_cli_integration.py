from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-agent-cli-integration.py"


def test_agent_cli_validator_checks_fallback_installers_without_persistent_state():
    payload = _run_validator("fallback-installers")

    statuses = {item["name"]: item["status"] for item in payload}
    assert statuses["fallback.claude_skills"] == "passed"
    assert statuses["fallback.claude_bootstrap_skill"] == "passed"
    assert statuses["fallback.cursor_adapter"] == "passed"
    assert statuses["fallback.cursor_rule"] == "passed"
    assert statuses["fallback.cursor_agents_file"] == "passed"


def test_agent_cli_validator_checks_claude_when_available():
    payload = _run_validator("claude")
    statuses = {item["name"]: item["status"] for item in payload}

    if statuses.get("claude.available") == "skipped":
        return

    assert statuses["claude.plugin_validate"] == "passed"
    assert statuses["claude.plugin_dir_flag"] == "passed"
    assert statuses["claude.persistent_install"] == "skipped"


def test_agent_cli_validator_checks_cursor_agent_when_available():
    payload = _run_validator("cursor")
    statuses = {item["name"]: item["status"] for item in payload}

    if statuses.get("cursor.available") == "skipped" or statuses.get("cursor.agent_available") == "skipped":
        return

    assert statuses["cursor_agent.plugin_dir_flag"] == "passed"
    assert statuses["cursor.persistent_install"] == "skipped"


def test_agent_cli_validator_checks_codex_when_available():
    payload = _run_validator("codex")
    statuses = {item["name"]: item["status"] for item in payload}

    if statuses.get("codex.available") == "skipped":
        return

    assert statuses["codex.plugin_list"] == "passed"
    assert statuses["codex.local_install"] == "skipped"


def _run_validator(tool: str) -> list[dict[str, str]]:
    result = subprocess.run(
        [str(SCRIPT), "--tool", tool, "--json"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    loaded = json.loads(result.stdout)
    assert isinstance(loaded, list)
    return loaded

