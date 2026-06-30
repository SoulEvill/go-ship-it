from pathlib import Path
import subprocess

import pytest
import yaml

from go_ship_it.cli import main
from go_ship_it.state import (
    CheckFailedError,
    GoShipitError,
    add_issue,
    register_repo,
    run_check,
    start_issue,
)


def test_run_check_executes_registered_test_command_in_worktree(tmp_path):
    root = _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")

    record = run_check(root, "issue-001", check="test")

    assert record.parent == root / "state" / "runs" / "issue-001" / "commands"
    data = yaml.safe_load(record.read_text())
    assert data["check"] == "test"
    assert data["command"] == "python -c 'print(\"ok\")'"
    assert data["cwd"] == str(root / "worktrees" / "sample" / "issue-001")
    assert data["exit_code"] == 0
    assert "ok" in data["stdout_tail"]
    assert data["stderr_tail"] == ""
    assert "started_at" in data
    assert "ended_at" in data

    journal = (root / "state" / "runs" / "issue-001" / "journal.md").read_text()
    assert "## Check: test" in journal
    assert "Exit code: 0" in journal


def test_run_check_records_failed_command(tmp_path):
    root = _started_issue_root(tmp_path, test_command="python -c 'import sys; print(\"bad\"); sys.exit(3)'")

    with pytest.raises(CheckFailedError) as exc_info:
        run_check(root, "issue-001", check="test")

    assert exc_info.value.exit_code == 3
    record = exc_info.value.record_file
    data = yaml.safe_load(record.read_text())
    assert data["exit_code"] == 3
    assert "bad" in data["stdout_tail"]

    journal = (root / "state" / "runs" / "issue-001" / "journal.md").read_text()
    assert "Exit code: 3" in journal


def test_run_check_rejects_missing_command(tmp_path):
    root = _started_issue_root(tmp_path, lint_command=None)

    with pytest.raises(GoShipitError, match="No lint command configured"):
        run_check(root, "issue-001", check="lint")

    commands_dir = root / "state" / "runs" / "issue-001" / "commands"
    assert not commands_dir.exists()


def test_main_run_check_returns_command_exit_code(tmp_path):
    root = _started_issue_root(tmp_path, test_command="python -c 'import sys; sys.exit(4)'")

    exit_code = main(["--root", str(root), "run-check", "issue-001", "--check", "test"])

    assert exit_code == 4
    records = list((root / "state" / "runs" / "issue-001" / "commands").glob("*.yaml"))
    assert len(records) == 1
    data = yaml.safe_load(records[0].read_text())
    assert data["exit_code"] == 4


def _started_issue_root(
    tmp_path: Path,
    *,
    setup_command: str | None = None,
    test_command: str | None = None,
    lint_command: str | None = None,
) -> Path:
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=setup_command,
        test_command=test_command,
        lint_command=lint_command,
    )
    add_issue(
        tmp_path,
        repo_id="sample",
        title="Change README",
        problem="README needs another line.",
        context="Use the test repo.",
        acceptance_criteria=["README changes."],
    )
    start_issue(tmp_path, "issue-001", claimed_by="test-thread")
    return tmp_path


def _create_git_repo(path: Path) -> Path:
    path.mkdir()
    _run_git(path, "init", "-b", "main")
    _run_git(path, "config", "user.email", "test@example.com")
    _run_git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("# Sample\n")
    _run_git(path, "add", "README.md")
    _run_git(path, "commit", "-m", "initial commit")
    return path


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)
