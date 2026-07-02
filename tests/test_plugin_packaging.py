import json
import os
from pathlib import Path
import subprocess
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_plugin_manifests_exist_and_versions_match_project():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version = project["project"]["version"]

    manifests = {
        ".claude-plugin/plugin.json": False,
        ".codex-plugin/plugin.json": True,
        ".cursor-plugin/plugin.json": True,
    }

    for relative, expects_skills_field in manifests.items():
        manifest = json.loads((ROOT / relative).read_text())
        assert manifest["name"] == "go-ship-it"
        assert manifest["version"] == version
        assert manifest["repository"] == "https://github.com/SoulEvill/go-ship-it"
        if expects_skills_field:
            assert manifest["skills"] == "./skills/"


def test_cursor_plugin_points_to_hook_config():
    manifest = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text())
    assert manifest["hooks"] == "./hooks/hooks-cursor.json"

    hooks = json.loads((ROOT / "hooks" / "hooks-cursor.json").read_text())
    assert hooks["version"] == 1
    assert hooks["hooks"]["sessionStart"][0]["command"] == "./hooks/run-hook.cmd session-start"


def test_session_start_hook_outputs_cursor_context():
    output = _run_hook({"CURSOR_PLUGIN_ROOT": str(ROOT)})
    payload = json.loads(output)

    assert "additional_context" in payload
    assert "You have GoShipit." in payload["additional_context"]
    assert "using-go-ship-it" in payload["additional_context"]


def test_session_start_hook_outputs_claude_context():
    output = _run_hook({"CLAUDE_PLUGIN_ROOT": str(ROOT)})
    payload = json.loads(output)

    context = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "You have GoShipit." in context
    assert "go-ship-it doctor" in context


def test_session_start_hook_outputs_generic_context():
    output = _run_hook({})
    payload = json.loads(output)

    assert "additionalContext" in payload
    assert "skills/using-go-ship-it/SKILL.md" in payload["additionalContext"]


def _run_hook(extra_env: dict[str, str]) -> str:
    env = os.environ.copy()
    env.update(extra_env)
    result = subprocess.run(
        ["bash", str(ROOT / "hooks" / "session-start")],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout
