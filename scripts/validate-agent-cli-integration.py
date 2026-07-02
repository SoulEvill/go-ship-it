#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate GoShipit agent CLI package integration.")
    parser.add_argument(
        "--tool",
        choices=["all", "claude", "cursor", "codex", "fallback-installers"],
        default="all",
        help="Integration surface to validate.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)

    results = _run_selected(args.tool)
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        for result in results:
            print(f"{result.status.upper()} {result.name}: {result.message}")
    return 1 if any(result.status == "failed" for result in results) else 0


def _run_selected(tool: str) -> list[CheckResult]:
    if tool == "claude":
        return _check_claude()
    if tool == "cursor":
        return _check_cursor()
    if tool == "codex":
        return _check_codex()
    if tool == "fallback-installers":
        return _check_fallback_installers()
    return _check_claude() + _check_cursor() + _check_codex() + _check_fallback_installers()


def _check_claude() -> list[CheckResult]:
    if shutil.which("claude") is None:
        return [CheckResult("claude.available", "skipped", "claude CLI not found on PATH")]

    results = [
        _run_check(
            "claude.plugin_validate",
            ["claude", "plugin", "validate", "--strict", str(ROOT)],
            "Claude plugin manifest validates in strict mode",
        ),
        _run_check(
            "claude.plugin_dir_flag",
            ["claude", "--plugin-dir", str(ROOT), "--help"],
            "Claude accepts the GoShipit repo as a session-local plugin directory",
            required_stdout="--plugin-dir",
        ),
    ]
    results.append(
        CheckResult(
            "claude.persistent_install",
            "skipped",
            "Claude local package validation uses --plugin-dir; persistent install requires marketplace setup",
        )
    )
    return results


def _check_cursor() -> list[CheckResult]:
    cursor_agent = shutil.which("cursor-agent")
    if cursor_agent is None:
        if shutil.which("cursor") is None:
            return [CheckResult("cursor.available", "skipped", "cursor CLI not found on PATH")]
        return [
            CheckResult(
                "cursor.agent_available",
                "skipped",
                "cursor-agent not found; install Cursor Agent before validating local plugin-dir loading",
            )
        ]

    return [
        _run_check(
            "cursor_agent.plugin_dir_flag",
            [cursor_agent, "--plugin-dir", str(ROOT), "--help"],
            "Cursor Agent accepts the GoShipit repo as a session-local plugin directory",
            required_stdout="--plugin-dir",
        ),
        CheckResult(
            "cursor.persistent_install",
            "skipped",
            "Cursor Agent local validation uses --plugin-dir; no persistent plugin install was created",
        ),
    ]


def _check_codex() -> list[CheckResult]:
    if shutil.which("codex") is None:
        return [CheckResult("codex.available", "skipped", "codex CLI not found on PATH")]

    return [
        _run_check(
            "codex.plugin_list",
            ["codex", "plugin", "list", "--json"],
            "Codex plugin command is available and returns JSON",
            json_stdout=True,
        ),
        CheckResult(
            "codex.local_install",
            "skipped",
            "Codex local plugin install is marketplace-based; no session-local plugin-dir check is available",
        ),
    ]


def _check_fallback_installers() -> list[CheckResult]:
    with tempfile.TemporaryDirectory(prefix="go-ship-it-agent-install-") as raw_tmp:
        tmp = Path(raw_tmp)
        claude_target = tmp / "claude" / "skills"
        cursor_target = tmp / "cursor-project"
        claude = _run_check(
            "fallback.claude_skills",
            [str(ROOT / "scripts" / "install-claude-skills.sh"), "--target", str(claude_target)],
            "Claude fallback skill copy installs into a temporary target",
        )
        cursor = _run_check(
            "fallback.cursor_adapter",
            [str(ROOT / "scripts" / "install-cursor-adapter.sh"), "--target", str(cursor_target)],
            "Cursor fallback adapter installs into a temporary target",
        )
        file_checks = [
            _path_check(
                "fallback.claude_bootstrap_skill",
                claude_target / "using-go-ship-it" / "SKILL.md",
                "Temporary Claude skill target includes using-go-ship-it",
            ),
            _path_check(
                "fallback.cursor_rule",
                cursor_target / ".cursor" / "rules" / "go-ship-it.mdc",
                "Temporary Cursor target includes GoShipit rule",
            ),
            _path_check(
                "fallback.cursor_agents_file",
                cursor_target / "AGENTS.md",
                "Temporary Cursor target includes AGENTS.md",
            ),
        ]
        return [claude, cursor, *file_checks]


def _run_check(
    name: str,
    command: list[str],
    success_message: str,
    *,
    required_stdout: str | None = None,
    json_stdout: bool = False,
) -> CheckResult:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, check=False, text=True)
    if result.returncode != 0:
        return CheckResult(name, "failed", _tail(result.stderr or result.stdout))
    if required_stdout is not None and required_stdout not in result.stdout:
        return CheckResult(name, "failed", f"expected stdout to include {required_stdout!r}")
    if json_stdout:
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return CheckResult(name, "failed", f"stdout was not valid JSON: {exc}")
    return CheckResult(name, "passed", success_message)


def _path_check(name: str, path: Path, success_message: str) -> CheckResult:
    if path.exists():
        return CheckResult(name, "passed", success_message)
    return CheckResult(name, "failed", f"missing expected path: {path}")


def _tail(text: str) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines[-8:]) if lines else "command failed without output"


if __name__ == "__main__":
    sys.exit(main())
