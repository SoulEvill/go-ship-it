from pathlib import Path
import subprocess

import pytest

from go_ship_it.state import (
    CheckFailedError,
    add_issue,
    append_note,
    cleanup_issue,
    export_run,
    register_repo,
    run_check,
    start_issue,
)


def test_export_run_writes_archived_issue_evidence_snapshot(tmp_path):
    root = _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")
    append_note(root, "issue-001", section="Investigation", note="Read README.", phase="investigate")
    run_check(root, "issue-001", check="test")
    cleanup_issue(root, "issue-001", destination="archive", note="Done.", remove_worktree=False)

    output = export_run(root, "issue-001", output=tmp_path / "docs" / "dogfood" / "issue-001-evidence.md")

    text = output.read_text()
    assert "# GoShipit Run Evidence: issue-001" in text
    assert "## Issue" in text
    assert "## Run Metadata" in text
    assert "## Journal" in text
    assert "Read README." in text
    assert "## Command Records" in text
    assert "- Check: `test`" in text
    assert "- Command: `python -c 'print(\"ok\")'`" in text
    assert "- Exit Code: `0`" in text
    assert "## Worktree" in text
    assert "worktrees/sample/issue-001" in text
    assert "## Notes" in text


def test_export_run_includes_failed_command_exit_code(tmp_path):
    root = _started_issue_root(tmp_path, test_command="python -c 'import sys; print(\"bad\"); sys.exit(3)'")
    with pytest.raises(CheckFailedError):
        run_check(root, "issue-001", check="test")

    output = export_run(root, "issue-001", output=tmp_path / "issue-001-failed-evidence.md")

    text = output.read_text()
    assert "- Exit Code: `3`" in text
    assert "bad" in text
    assert "passed" not in text.lower()


def test_export_run_fails_for_missing_issue_and_run(tmp_path):
    with pytest.raises(FileNotFoundError, match="No issue or run evidence"):
        export_run(tmp_path, "issue-999", output=tmp_path / "out.md")


def _started_issue_root(tmp_path: Path, *, test_command: str) -> Path:
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=test_command,
        lint_command=None,
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
