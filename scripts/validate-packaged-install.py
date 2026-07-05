#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class AcceptanceReport:
    temp_root: str
    results: list[CheckResult]

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.results if result.status == "passed")

    @property
    def skipped_count(self) -> int:
        return sum(1 for result in self.results if result.status == "skipped")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a built GoShipit wheel in a fresh temporary room.")
    parser.add_argument("--wheel", default=None, help="Path to a built go_ship_it wheel. Defaults to latest dist wheel.")
    parser.add_argument("--python", default=sys.executable, help="Python executable used to create the temporary venv.")
    parser.add_argument("--temp-root", default=None, help="Use this directory as the fresh room.")
    parser.add_argument("--keep-temp", action="store_true", help="Keep the temporary room after validation.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)

    wheel = Path(args.wheel).resolve() if args.wheel else _latest_wheel()
    temp_root = Path(args.temp_root).resolve() if args.temp_root else None
    report = run_acceptance(
        wheel=wheel,
        python=args.python,
        temp_root=temp_root,
        keep_temp=args.keep_temp,
    )
    if args.json:
        payload = {
            "temp_root": report.temp_root,
            "passed": report.passed_count,
            "failed": report.failed_count,
            "skipped": report.skipped_count,
            "results": [asdict(result) for result in report.results],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Fresh room: {report.temp_root}")
        for result in report.results:
            print(f"{result.status.upper()} {result.name}: {result.message}")
    return 1 if report.failed_count else 0


def run_acceptance(
    *,
    wheel: Path,
    python: str,
    temp_root: Path | None = None,
    keep_temp: bool = False,
) -> AcceptanceReport:
    if temp_root is not None:
        temp_root.mkdir(parents=True, exist_ok=True)
        return _run_in_room(wheel=wheel, python=python, temp_root=temp_root)

    if keep_temp:
        owned_root = Path(tempfile.mkdtemp(prefix="go-ship-it-packaged-install-"))
        return _run_in_room(wheel=wheel, python=python, temp_root=owned_root)

    with tempfile.TemporaryDirectory(prefix="go-ship-it-packaged-install-") as raw_tmp:
        return _run_in_room(wheel=wheel, python=python, temp_root=Path(raw_tmp))


def _run_in_room(*, wheel: Path, python: str, temp_root: Path) -> AcceptanceReport:
    results: list[CheckResult] = []
    venv = temp_root / "venv"
    control_root = temp_root / "control"
    go_ship_it = _venv_bin(venv) / _exe_name("go-ship-it")

    if not wheel.exists():
        return AcceptanceReport(
            temp_root=str(temp_root),
            results=[CheckResult("install.wheel_exists", "failed", f"missing wheel: {wheel}")],
        )
    results.append(CheckResult("install.wheel_exists", "passed", f"wheel exists: {wheel}"))

    venv_check = _command_check("install.venv", [python, "-m", "venv", str(venv)], "created temporary venv")
    results.append(venv_check)
    if venv_check.status == "failed":
        return AcceptanceReport(temp_root=str(temp_root), results=results)

    install_check = _command_check(
        "install.wheel",
        [
            str(_venv_python(venv)),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            str(wheel),
        ],
        "installed wheel into temporary venv",
    )
    results.append(install_check)
    if install_check.status == "failed":
        return AcceptanceReport(temp_root=str(temp_root), results=results)

    package_root_result = _run_command([str(go_ship_it), "package-root"])
    if package_root_result.returncode == 0:
        package_root = Path(package_root_result.stdout.strip())
        results.append(CheckResult("cli.package_root", "passed", f"package root: {package_root}"))
        results.extend(_check_package_root(package_root))
    else:
        package_root = temp_root / "missing-package-root"
        results.append(CheckResult("cli.package_root", "failed", _tail(package_root_result.stderr or package_root_result.stdout)))

    results.append(_command_check("cli.init", [str(go_ship_it), "--root", str(control_root), "init"], "initialized control root"))
    results.extend(_check_control_root(control_root))
    results.append(_command_check("cli.doctor", [str(go_ship_it), "--root", str(control_root), "doctor"], "doctor passed in fresh control root"))
    results.extend(_run_first_issue_flow(go_ship_it=go_ship_it, temp_root=temp_root, control_root=control_root))
    results.extend(_check_agent_clis(package_root))
    return AcceptanceReport(temp_root=str(temp_root), results=results)


def _check_package_root(package_root: Path) -> list[CheckResult]:
    required = {
        "package.skill": package_root / "skills" / "using-go-ship-it" / "SKILL.md",
        "package.claude_manifest": package_root / ".claude-plugin" / "plugin.json",
        "package.codex_manifest": package_root / ".codex-plugin" / "plugin.json",
        "package.cursor_manifest": package_root / ".cursor-plugin" / "plugin.json",
        "package.hook_session_start": package_root / "hooks" / "session-start",
        "package.hook_runner": package_root / "hooks" / "run-hook.cmd",
        "package.cursor_hooks": package_root / "hooks" / "hooks-cursor.json",
    }
    return [
        CheckResult(name, "passed", f"found {path}")
        if path.exists()
        else CheckResult(name, "failed", f"missing {path}")
        for name, path in required.items()
    ]


def _check_control_root(control_root: Path) -> list[CheckResult]:
    required = {
        "control.state_repos": control_root / "state" / "repos",
        "control.worktrees": control_root / "worktrees",
    }
    return [
        CheckResult(name, "passed", f"found {path}")
        if path.exists()
        else CheckResult(name, "failed", f"missing {path}")
        for name, path in required.items()
    ]


def _run_first_issue_flow(*, go_ship_it: Path, temp_root: Path, control_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    target_repo = temp_root / "target-repo"
    results.append(_create_target_repo(target_repo))
    if results[-1].status == "failed":
        return results

    success_messages = {
        "flow.init_repo": "register target repo during init",
        "flow.add_issue": "add first issue",
        "flow.start_issue": "start first issue",
        "flow.status_json": "status JSON reports active issue",
        "flow.investigation_note": "record investigation evidence",
        "flow.phase_propose": "move to proposal",
        "flow.proposal_note": "record proposal evidence",
        "flow.phase_implement": "move to implementation",
        "flow.implementation_note": "record implementation evidence",
        "flow.phase_test": "move to test",
        "flow.append_acceptance_note": "record acceptance evidence",
        "flow.run_check": "record test command evidence",
        "flow.handoff": "write handoff",
        "flow.export": "export run evidence",
        "flow.verify_strict": "strict verification passed",
        "flow.cleanup_archive": "archive and remove worktree",
        "flow.final_doctor": "doctor passed after cleanup",
    }
    command_map = {
        "flow.init_repo": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "init",
            "--repo-id",
            "target",
            "--repo-path",
            str(target_repo),
            "--test-command",
            "python -c 'print(\"ok\")'",
        ],
        "flow.add_issue": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "add-issue",
            "--repo",
            "target",
            "--title",
            "Change README",
            "--problem",
            "README needs one small change.",
            "--context",
            "Disposable packaged install smoke.",
            "--acceptance",
            "README changes.",
        ],
        "flow.start_issue": [str(go_ship_it), "--root", str(control_root), "start-issue", "target/issue-001"],
        "flow.status_json": [str(go_ship_it), "--root", str(control_root), "status", "--json"],
        "flow.investigation_note": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "append-note",
            "target/issue-001",
            "--section",
            "Investigation",
            "--phase",
            "investigate",
            "--note",
            "Read the disposable target README.",
        ],
        "flow.phase_propose": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "set-phase",
            "target/issue-001",
            "propose",
            "--note",
            "Investigation complete.",
        ],
        "flow.proposal_note": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "append-note",
            "target/issue-001",
            "--section",
            "Proposal",
            "--phase",
            "propose",
            "--note",
            "Use the smallest README-only change.",
        ],
        "flow.phase_implement": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "set-phase",
            "target/issue-001",
            "implement",
            "--note",
            "Proposal accepted for smoke flow.",
        ],
        "flow.implementation_note": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "append-note",
            "target/issue-001",
            "--section",
            "Implementation",
            "--phase",
            "implement",
            "--note",
            "No target mutation needed for packaged install smoke.",
        ],
        "flow.phase_test": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "set-phase",
            "target/issue-001",
            "test",
            "--note",
            "Ready for smoke checks.",
        ],
        "flow.append_acceptance_note": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "append-note",
            "target/issue-001",
            "--section",
            "Review",
            "--phase",
            "test",
            "--note",
            "Acceptance evidence: README changes. Covered by the smoke test command.",
        ],
        "flow.run_check": [str(go_ship_it), "--root", str(control_root), "run-check", "target/issue-001", "--check", "test"],
        "flow.handoff": [str(go_ship_it), "--root", str(control_root), "handoff", "target/issue-001", "--write"],
        "flow.export": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "export-run",
            "target/issue-001",
            "--output",
            "docs/dogfood/target-issue-001-evidence.md",
        ],
        "flow.verify_strict": [str(go_ship_it), "--root", str(control_root), "verify-run", "target/issue-001", "--strict"],
        "flow.cleanup_archive": [
            str(go_ship_it),
            "--root",
            str(control_root),
            "cleanup-issue",
            "target/issue-001",
            "--destination",
            "archive",
            "--note",
            "Packaged install smoke complete.",
            "--remove-worktree",
        ],
        "flow.final_doctor": [str(go_ship_it), "--root", str(control_root), "doctor"],
    }
    for name, command in command_map.items():
        result = _command_check(name, command, success_messages[name])
        results.append(result)
        if result.status == "failed":
            break
    return results


def _create_target_repo(target_repo: Path) -> CheckResult:
    target_repo.mkdir(parents=True, exist_ok=True)
    (target_repo / "README.md").write_text("# Packaged Install Smoke\n")
    commands = [
        ["git", "init", "-b", "main"],
        ["git", "config", "user.email", "go-ship-it@example.invalid"],
        ["git", "config", "user.name", "GoShipit Smoke"],
        ["git", "add", "README.md"],
        ["git", "commit", "-m", "initial commit"],
    ]
    for command in commands:
        result = _run_command(command, cwd=target_repo)
        if result.returncode != 0:
            return CheckResult("flow.target_repo", "failed", _tail(result.stderr or result.stdout))
    return CheckResult("flow.target_repo", "passed", f"created disposable git repo: {target_repo}")


def _check_agent_clis(package_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    claude = shutil.which("claude")
    if claude is None:
        results.append(CheckResult("claude.available", "skipped", "claude CLI not found on PATH"))
    else:
        results.append(
            _command_check(
                "claude.plugin_dir",
                [claude, "--plugin-dir", str(package_root), "--help"],
                "Claude accepts installed package root as --plugin-dir",
            )
        )

    cursor_agent = shutil.which("cursor-agent")
    if cursor_agent is None:
        results.append(CheckResult("cursor_agent.available", "skipped", "cursor-agent not found on PATH"))
    else:
        results.append(
            _command_check(
                "cursor_agent.plugin_dir",
                [cursor_agent, "--plugin-dir", str(package_root), "--help"],
                "Cursor Agent accepts installed package root as --plugin-dir",
            )
        )

    codex = shutil.which("codex")
    if codex is None:
        results.append(CheckResult("codex.available", "skipped", "codex CLI not found on PATH"))
    else:
        results.append(_command_check("codex.plugin_list", [codex, "plugin", "list", "--json"], "Codex plugin command is available"))
    return results


def _command_check(name: str, command: list[str], success_message: str, *, cwd: Path | None = None) -> CheckResult:
    result = _run_command(command, cwd=cwd)
    if result.returncode == 0:
        return CheckResult(name, "passed", success_message)
    return CheckResult(name, "failed", _tail(result.stderr or result.stdout))


def _run_command(command: list[str], *, cwd: Path | None = None) -> CommandResult:
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env.setdefault("PIP_CACHE_DIR", str(Path(tempfile.gettempdir()) / "go-ship-it-pip-cache"))
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, check=False, text=True, env=env)
    except FileNotFoundError as exc:
        return CommandResult(command=command, returncode=127, stdout="", stderr=str(exc))
    return CommandResult(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def _latest_wheel() -> Path:
    wheels = sorted((ROOT / "dist").glob("go_ship_it-*.whl"), key=lambda path: path.stat().st_mtime)
    if not wheels:
        raise SystemExit("No built wheel found in dist/. Run `uv build` first or pass --wheel.")
    return wheels[-1].resolve()


def _venv_bin(venv: Path) -> Path:
    return venv / ("Scripts" if os.name == "nt" else "bin")


def _venv_python(venv: Path) -> Path:
    return _venv_bin(venv) / _exe_name("python")


def _exe_name(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def _tail(text: str) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines[-8:]) if lines else "command failed without output"


if __name__ == "__main__":
    sys.exit(main())
