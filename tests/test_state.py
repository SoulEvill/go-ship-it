from pathlib import Path
import subprocess

import pytest

from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import (
    IssueAlreadyActiveError,
    add_issue,
    cleanup_issue,
    ensure_layout,
    next_issue_id,
    register_repo,
    start_issue,
)


def test_ensure_layout_creates_state_directories(tmp_path):
    ensure_layout(tmp_path)

    assert (tmp_path / "state" / "repos").is_dir()
    assert (tmp_path / "state" / "issues" / "todo").is_dir()
    assert (tmp_path / "state" / "issues" / "execution").is_dir()
    assert (tmp_path / "state" / "issues" / "archive").is_dir()
    assert (tmp_path / "state" / "runs").is_dir()
    assert (tmp_path / "worktrees").is_dir()


def test_register_repo_writes_simple_registry_file(tmp_path):
    target = tmp_path / "target"
    target.mkdir()

    repo_file = register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command="uv sync",
        test_command="uv run pytest",
        lint_command=None,
    )

    assert repo_file == tmp_path / "state" / "repos" / "sample.yaml"
    assert repo_file.read_text() == (
        "id: sample\n"
        f"path: {target}\n"
        "default_branch: main\n"
        "worktree_root: worktrees/sample\n"
        "setup_command: uv sync\n"
        "test_command: uv run pytest\n"
        "lint_command: null\n"
    )


def test_add_issue_creates_todo_markdown(tmp_path):
    register_repo(
        tmp_path,
        repo_id="parawave",
        path=tmp_path / "parawave",
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )

    issue_file = add_issue(
        tmp_path,
        repo_id="parawave",
        title="Add resume example coverage",
        problem="The README mentions resume behavior but examples do not cover it.",
        context="Use the sibling parawave repo.",
        acceptance_criteria=["A focused test exists.", "The test passes."],
    )

    assert issue_file == tmp_path / "state" / "issues" / "todo" / "issue-001.md"
    metadata, body = parse_frontmatter(issue_file.read_text())
    assert metadata["id"] == "issue-001"
    assert metadata["repo"] == "parawave"
    assert metadata["status"] == "todo"
    assert metadata["phase"] == "setup"
    assert isinstance(metadata["created_at"], str)
    assert metadata["worktree"] is None
    assert metadata["branch"] is None
    assert "## Problem" in body
    assert "- A focused test exists." in body


def test_add_issue_rejects_unregistered_repo(tmp_path):
    ensure_layout(tmp_path)

    with pytest.raises(FileNotFoundError, match="Repo registry file not found"):
        add_issue(
            tmp_path,
            repo_id="typo",
            title="Unknown repo issue",
            problem="This repo id is not registered.",
            context="",
            acceptance_criteria=["No issue should be created."],
        )

    assert not list((tmp_path / "state" / "issues" / "todo").glob("issue-*.md"))


def test_next_issue_id_counts_preserved_managed_worktrees(tmp_path):
    ensure_layout(tmp_path)
    (tmp_path / "worktrees" / "sample" / "issue-001").mkdir(parents=True)

    assert next_issue_id(tmp_path) == "issue-002"


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)


def _git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True, text=True)
    return result.stdout


def _create_git_repo(path: Path) -> Path:
    path.mkdir()
    _run_git(path, "init", "-b", "main")
    _run_git(path, "config", "user.email", "test@example.com")
    _run_git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("# Sample\n")
    _run_git(path, "add", "README.md")
    _run_git(path, "commit", "-m", "initial commit")
    return path


def _add_sample_issue(root: Path, *, title: str = "Change README") -> Path:
    return add_issue(
        root,
        repo_id="sample",
        title=title,
        problem="README needs another line.",
        context="Use the test repo.",
        acceptance_criteria=["README changes."],
    )


def test_start_issue_claims_issue_and_creates_worktree(tmp_path):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command="pytest",
        lint_command=None,
    )
    _add_sample_issue(tmp_path)

    run = start_issue(tmp_path, "issue-001", claimed_by="test-thread")

    assert run.issue_id == "issue-001"
    assert run.branch == "go-ship-it/issue-001"
    assert run.worktree == tmp_path / "worktrees" / "sample" / "issue-001"
    assert (run.worktree / "README.md").exists()
    assert not (tmp_path / "state" / "issues" / "todo" / "issue-001.md").exists()
    execution_file = tmp_path / "state" / "issues" / "execution" / "issue-001.md"
    metadata, _body = parse_frontmatter(execution_file.read_text())
    assert metadata["status"] == "execution"
    assert metadata["phase"] == "investigate"
    assert metadata["branch"] == "go-ship-it/issue-001"
    assert metadata["worktree"] == "worktrees/sample/issue-001"
    assert (tmp_path / "state" / "runs" / "issue-001" / "claim.lock").is_dir()
    run_file = tmp_path / "state" / "runs" / "issue-001" / "run.yaml"
    assert run_file.exists()
    assert "claimed_by: test-thread\n" in run_file.read_text()


def test_start_issue_rejects_duplicate_active_run(tmp_path):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)
    start_issue(tmp_path, "issue-001", claimed_by="first-thread")

    with pytest.raises(IssueAlreadyActiveError) as exc_info:
        start_issue(tmp_path, "issue-001", claimed_by="second-thread")
    message = str(exc_info.value)
    assert "issue-001 already has an active run" in message
    assert "state/issues/execution/issue-001.md" in message
    assert "worktrees/sample/issue-001" in message


def test_start_issue_supports_two_active_issues_for_same_repo(tmp_path):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path, title="First")
    _add_sample_issue(tmp_path, title="Second")

    first = start_issue(tmp_path, "issue-001", claimed_by="first-thread")
    second = start_issue(tmp_path, "issue-002", claimed_by="second-thread")

    assert first.worktree == tmp_path / "worktrees" / "sample" / "issue-001"
    assert second.worktree == tmp_path / "worktrees" / "sample" / "issue-002"
    assert first.worktree.exists()
    assert second.worktree.exists()


def test_start_issue_leaves_todo_unmoved_when_target_repo_is_missing(tmp_path):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=tmp_path / "missing",
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)

    with pytest.raises(FileNotFoundError):
        start_issue(tmp_path, "issue-001", claimed_by="test-thread")

    assert (tmp_path / "state" / "issues" / "todo" / "issue-001.md").exists()
    assert not (tmp_path / "state" / "issues" / "execution" / "issue-001.md").exists()
    assert not (tmp_path / "state" / "runs" / "issue-001" / "claim.lock").exists()
    assert not (tmp_path / "worktrees" / "sample" / "issue-001").exists()


def _started_issue_root(tmp_path: Path) -> Path:
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)
    start_issue(tmp_path, "issue-001", claimed_by="test-thread")
    return tmp_path


def test_cleanup_return_to_todo_moves_issue_back_and_removes_active_worktree(tmp_path):
    root = _started_issue_root(tmp_path)

    active_worktree = root / "worktrees" / "sample" / "issue-001"
    assert active_worktree.exists()

    result = cleanup_issue(root, "issue-001", destination="todo", note="Needs a clearer ask.", remove_worktree=True)

    assert result == root / "state" / "issues" / "todo" / "issue-001.md"
    assert result.exists()
    assert not active_worktree.exists()
    assert not (root / "state" / "issues" / "execution" / "issue-001.md").exists()
    metadata, _body = parse_frontmatter(result.read_text())
    assert metadata["status"] == "todo"
    assert metadata["phase"] == "setup"
    assert metadata["worktree"] is None
    assert metadata["branch"] is None
    assert (root / "state" / "runs" / "issue-001" / "run.yaml").exists()
    assert "cleanup_destination: todo\n" in (root / "state" / "runs" / "issue-001" / "run.yaml").read_text()
    assert "Needs a clearer ask." in (root / "state" / "runs" / "issue-001" / "journal.md").read_text()
    assert not (root / "state" / "runs" / "issue-001" / "claim.lock").exists()
    assert "go-ship-it/issue-001" not in _git_output(root / "target", "branch", "--list", "go-ship-it/issue-001")


def test_cleanup_return_to_todo_requires_worktree_removal(tmp_path):
    root = _started_issue_root(tmp_path)

    with pytest.raises(ValueError, match="returning an issue to todo requires remove_worktree=True"):
        cleanup_issue(root, "issue-001", destination="todo", note="Needs a clearer ask.", remove_worktree=False)

    assert (root / "state" / "issues" / "execution" / "issue-001.md").exists()
    assert (root / "worktrees" / "sample" / "issue-001").exists()
    assert (root / "state" / "runs" / "issue-001" / "claim.lock").exists()


def test_cleanup_archive_moves_issue_to_archive_and_preserves_worktree(tmp_path):
    root = _started_issue_root(tmp_path)
    active_worktree = root / "worktrees" / "sample" / "issue-001"

    result = cleanup_issue(root, "issue-001", destination="archive", note="Closed after review.", remove_worktree=False)

    assert result == root / "state" / "issues" / "archive" / "issue-001.md"
    assert result.exists()
    assert active_worktree.exists()
    assert not (root / "state" / "issues" / "execution" / "issue-001.md").exists()
    metadata, body = parse_frontmatter(result.read_text())
    assert metadata["status"] == "archive"
    assert metadata["phase"] == "cleanup"
    assert "Closed after review." in body
    assert not (root / "state" / "runs" / "issue-001" / "claim.lock").exists()


def test_cleanup_archive_can_remove_managed_worktree(tmp_path):
    root = _started_issue_root(tmp_path)
    active_worktree = root / "worktrees" / "sample" / "issue-001"

    cleanup_issue(root, "issue-001", destination="archive", note="Closed after review.", remove_worktree=True)

    assert not active_worktree.exists()
