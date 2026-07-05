from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_packaged_install_acceptance_checks_fresh_room_and_agent_clis(tmp_path, monkeypatch):
    module = _load_script()
    wheel = tmp_path / "go_ship_it-0.1.0-py3-none-any.whl"
    wheel.write_text("fake wheel")
    temp_root = tmp_path / "fresh-room"
    package_root = tmp_path / "installed-package"
    _write_package_root(package_root)
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path | None = None) -> object:
        calls.append(command)
        if command[:2] == ["git", "init"]:
            return module.CommandResult(command=command, returncode=0, stdout="", stderr="")
        if command[:2] == ["git", "config"]:
            return module.CommandResult(command=command, returncode=0, stdout="", stderr="")
        if command[:2] == ["git", "add"]:
            return module.CommandResult(command=command, returncode=0, stdout="", stderr="")
        if command[:2] == ["git", "commit"]:
            return module.CommandResult(command=command, returncode=0, stdout="", stderr="")
        if command[:3] == [sys.executable, "-m", "venv"]:
            return module.CommandResult(command=command, returncode=0, stdout="", stderr="")
        if command[1:4] == ["-m", "pip", "install"]:
            return module.CommandResult(command=command, returncode=0, stdout="", stderr="")
        if command[-1] == "package-root":
            return module.CommandResult(command=command, returncode=0, stdout=f"{package_root}\n", stderr="")
        if "init" in command:
            control_root = Path(command[2])
            for relative in ("state/repos", "worktrees"):
                (control_root / relative).mkdir(parents=True, exist_ok=True)
            return module.CommandResult(command=command, returncode=0, stdout="", stderr="")
        if "add-issue" in command:
            return module.CommandResult(command=command, returncode=0, stdout=str(temp_root / "control" / "state" / "repos" / "target" / "issues" / "todo" / "issue-001" / "issue.md"), stderr="")
        if "start-issue" in command:
            return module.CommandResult(command=command, returncode=0, stdout="Issue: target/issue-001\n", stderr="")
        if "status" in command and "--json" in command:
            return module.CommandResult(command=command, returncode=0, stdout='{"summary": {"execution": 1}, "active": [{"repo_id": "target", "issue_id": "issue-001", "issue_ref": "target/issue-001"}]}\n', stderr="")
        if "append-note" in command:
            return module.CommandResult(command=command, returncode=0, stdout=str(temp_root / "control" / "state" / "repos" / "target" / "issues" / "execution" / "issue-001" / "notes.md"), stderr="")
        if "run-check" in command:
            return module.CommandResult(command=command, returncode=0, stdout=str(temp_root / "control" / "state" / "repos" / "target" / "issues" / "execution" / "issue-001" / "logs" / "commands" / "test.yaml"), stderr="")
        if "handoff" in command:
            return module.CommandResult(command=command, returncode=0, stdout=str(temp_root / "control" / "state" / "repos" / "target" / "issues" / "execution" / "issue-001" / "handoff.md"), stderr="")
        if "export-run" in command:
            return module.CommandResult(
                command=command,
                returncode=0,
                stdout=str(
                    temp_root
                    / "control"
                    / "state"
                    / "repos"
                    / "target"
                    / "issues"
                    / "execution"
                    / "issue-001"
                    / "evidence.md"
                ),
                stderr="",
            )
        if "verify-run" in command and "--strict" in command:
            return module.CommandResult(command=command, returncode=0, stdout="# GoShipit Run Verification\n", stderr="")
        if "cleanup-issue" in command:
            return module.CommandResult(command=command, returncode=0, stdout=str(temp_root / "control" / "state" / "repos" / "target" / "issues" / "archive" / "issue-001" / "issue.md"), stderr="")
        if command[-1] == "doctor":
            return module.CommandResult(command=command, returncode=0, stdout="# GoShipit Doctor\n", stderr="")
        return module.CommandResult(command=command, returncode=0, stdout="--plugin-dir\n", stderr="")

    monkeypatch.setattr(module, "_run_command", fake_run)
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/fake/{name}" if name in {"claude", "cursor-agent"} else None)

    report = module.run_acceptance(
        wheel=wheel,
        python=sys.executable,
        temp_root=temp_root,
        keep_temp=True,
    )

    assert report.failed_count == 0
    assert {result.name for result in report.results} >= {
        "install.venv",
        "install.wheel",
        "cli.package_root",
        "cli.init",
        "cli.doctor",
        "flow.target_repo",
        "flow.init_repo",
        "flow.add_issue",
        "flow.start_issue",
        "flow.status_json",
        "flow.append_acceptance_note",
        "flow.run_check",
        "flow.handoff",
        "flow.export",
        "flow.verify_strict",
        "flow.cleanup_archive",
        "flow.final_doctor",
        "claude.plugin_dir",
        "cursor_agent.plugin_dir",
    }
    assert [sys.executable, "-m", "venv", str(temp_root / "venv")] in calls
    assert [str(temp_root / "venv" / "bin" / "go-ship-it"), "--root", str(temp_root / "control"), "doctor"] in calls
    assert [
        str(temp_root / "venv" / "bin" / "go-ship-it"),
        "--root",
        str(temp_root / "control"),
        "export-run",
        "target/issue-001",
    ] in calls
    assert [
        str(temp_root / "venv" / "bin" / "go-ship-it"),
        "--root",
        str(temp_root / "control"),
        "verify-run",
        "target/issue-001",
        "--strict",
    ] in calls
    assert ["/fake/claude", "--plugin-dir", str(package_root), "--help"] in calls
    assert ["/fake/cursor-agent", "--plugin-dir", str(package_root), "--help"] in calls


def test_packaged_install_acceptance_skips_missing_agent_clis(tmp_path, monkeypatch):
    module = _load_script()
    wheel = tmp_path / "go_ship_it-0.1.0-py3-none-any.whl"
    wheel.write_text("fake wheel")
    package_root = tmp_path / "installed-package"
    _write_package_root(package_root)

    def fake_run(command: list[str], *, cwd: Path | None = None) -> object:
        if command[-1] == "package-root":
            return module.CommandResult(command=command, returncode=0, stdout=f"{package_root}\n", stderr="")
        if command[-1] == "init":
            control_root = Path(command[2])
            (control_root / "state" / "repos").mkdir(parents=True, exist_ok=True)
            (control_root / "worktrees").mkdir(parents=True, exist_ok=True)
        return module.CommandResult(command=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module, "_run_command", fake_run)
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)

    report = module.run_acceptance(
        wheel=wheel,
        python=sys.executable,
        temp_root=tmp_path / "fresh-room",
        keep_temp=True,
    )

    statuses = {result.name: result.status for result in report.results}
    assert statuses["claude.available"] == "skipped"
    assert statuses["cursor_agent.available"] == "skipped"
    assert report.failed_count == 0


def test_packaged_install_acceptance_stops_when_wheel_install_fails(tmp_path, monkeypatch):
    module = _load_script()
    wheel = tmp_path / "go_ship_it-0.1.0-py3-none-any.whl"
    wheel.write_text("fake wheel")
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path | None = None) -> object:
        calls.append(command)
        if command[:3] == [sys.executable, "-m", "venv"]:
            return module.CommandResult(command=command, returncode=0, stdout="", stderr="")
        if command[1:4] == ["-m", "pip", "install"]:
            return module.CommandResult(command=command, returncode=1, stdout="", stderr="no pyyaml")
        raise AssertionError(f"unexpected command after failed install: {command}")

    monkeypatch.setattr(module, "_run_command", fake_run)

    report = module.run_acceptance(
        wheel=wheel,
        python=sys.executable,
        temp_root=tmp_path / "fresh-room",
        keep_temp=True,
    )

    statuses = {result.name: result.status for result in report.results}
    assert statuses["install.venv"] == "passed"
    assert statuses["install.wheel"] == "failed"
    assert report.failed_count == 1
    assert all(command[-1] != "package-root" for command in calls)


def _load_script():
    path = ROOT / "scripts" / "validate-packaged-install.py"
    spec = importlib.util.spec_from_file_location("validate_packaged_install", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_package_root(path: Path) -> None:
    (path / "skills" / "using-go-ship-it").mkdir(parents=True)
    (path / "skills" / "using-go-ship-it" / "SKILL.md").write_text("# Using GoShipit\n")
    (path / ".claude-plugin").mkdir()
    (path / ".claude-plugin" / "plugin.json").write_text("{}")
    (path / ".codex-plugin").mkdir()
    (path / ".codex-plugin" / "plugin.json").write_text("{}")
    (path / ".cursor-plugin").mkdir()
    (path / ".cursor-plugin" / "plugin.json").write_text("{}")
    (path / "hooks").mkdir()
    (path / "hooks" / "session-start").write_text("#!/usr/bin/env bash\n")
    (path / "hooks" / "run-hook.cmd").write_text("#!/usr/bin/env bash\n")
    (path / "hooks" / "hooks-cursor.json").write_text("{}")
