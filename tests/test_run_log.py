from pathlib import Path
import subprocess

import pytest

from go_ship_it.state import (
    add_issue,
    append_run_log,
    cleanup_issue,
    read_run_log,
    register_repo,
    start_issue,
)


def test_append_run_log_creates_comment_with_sources(tmp_path):
    root = _started_issue_root(tmp_path)

    path = append_run_log(
        root,
        "issue-001",
        note="Agent started from the target repo and recovered with --root.",
        author="codex",
        sources=[
            "transcript:/tmp/session.jsonl",
            "command:state/runs/issue-001/commands/test.yaml",
        ],
    )

    text = path.read_text()
    assert path == root / "state" / "runs" / "issue-001" / "run-log.md"
    assert "Author: codex" in text
    assert "- transcript:/tmp/session.jsonl" in text
    assert "- command:state/runs/issue-001/commands/test.yaml" in text
    assert "Agent started from the target repo" in text


def test_append_run_log_supports_archived_runs(tmp_path):
    root = _started_issue_root(tmp_path)
    cleanup_issue(root, "issue-001", destination="archive", note="Done.", remove_worktree=False)

    path = append_run_log(root, "issue-001", note="Captured after cleanup.", author=None, sources=[])

    assert "Captured after cleanup." in path.read_text()


def test_append_run_log_fails_without_run_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match="Run directory not found"):
        append_run_log(tmp_path, "issue-999", note="No run.", author=None, sources=[])


def test_read_run_log_returns_empty_string_when_missing(tmp_path):
    root = _started_issue_root(tmp_path)

    assert read_run_log(root, "issue-001") == ""


def test_read_run_log_returns_existing_text(tmp_path):
    root = _started_issue_root(tmp_path)
    append_run_log(root, "issue-001", note="Something happened.", author="human", sources=[])

    assert "Something happened." in read_run_log(root, "issue-001")


def _started_issue_root(tmp_path: Path) -> Path:
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command="python -c 'print(\"ok\")'",
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
