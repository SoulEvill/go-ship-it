from pathlib import Path
import subprocess

import pytest
import yaml

import go_ship_it.pull_request as pr_module
from go_ship_it.pull_request import prepare_pull_request, publish_pull_request
from go_ship_it.state import (
    GoShipitError,
    add_issue,
    register_repo,
    run_check,
    start_issue,
    update_repo_config,
    write_handoff,
)


def test_prepare_pull_request_writes_issue_local_preview(tmp_path):
    root = _started_issue_root(tmp_path)
    worktree = root / "worktrees" / "sample" / "issue-001"
    (worktree / "README.md").write_text("# Sample\n\nMore detail.\n")

    preview = prepare_pull_request(root, "sample/issue-001", branch="feature/readme-change")

    assert preview.path == root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "pr.md"
    assert preview.branch == "feature/readme-change"
    text = preview.path.read_text()
    assert "Local work branch: `go-ship-it/issue-001`" in text
    assert "PR branch: `feature/readme-change`" in text
    assert "The worktree has uncommitted changes" in text
    run = yaml.safe_load(
        (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "run.yaml").read_text()
    )
    assert run["pull_request"]["body_file"] == "state/repos/sample/issues/execution/issue-001/pr.md"
    assert run["pull_request"]["branch"] == "feature/readme-change"


def test_prepare_pull_request_requires_branch_first_time(tmp_path):
    root = _started_issue_root(tmp_path)

    with pytest.raises(ValueError, match="PR branch is required"):
        prepare_pull_request(root, "sample/issue-001")


def test_prepare_pull_request_reuses_recorded_issue_branch(tmp_path):
    root = _started_issue_root(tmp_path)
    prepare_pull_request(root, "sample/issue-001", branch="feature/readme")

    preview = prepare_pull_request(root, "sample/issue-001")

    assert preview.branch == "feature/readme"


def test_prepare_pull_request_accepts_explicit_branch(tmp_path):
    root = _started_issue_root(tmp_path)

    preview = prepare_pull_request(root, "sample/issue-001", branch="bugfix/readme")

    assert preview.branch == "bugfix/readme"


def test_publish_pull_request_requires_approval_when_auto_publish_disabled(tmp_path):
    root = _started_issue_root(tmp_path)
    prepare_pull_request(root, "sample/issue-001", branch="feature/readme")

    with pytest.raises(GoShipitError, match="requires explicit approval"):
        publish_pull_request(root, "sample/issue-001")


def test_publish_pull_request_rejects_dirty_worktree(tmp_path):
    root = _started_issue_root(tmp_path)
    worktree = root / "worktrees" / "sample" / "issue-001"
    (worktree / "README.md").write_text("# Sample\n\nMore detail.\n")
    prepare_pull_request(root, "sample/issue-001", branch="feature/readme")

    with pytest.raises(GoShipitError, match="uncommitted changes"):
        publish_pull_request(root, "sample/issue-001", approved=True)


def test_publish_pull_request_pushes_pr_branch_and_records_url(tmp_path, monkeypatch):
    root = _started_issue_root(tmp_path)
    target = root / "target"
    remote = tmp_path / "remote.git"
    _run_git(remote.parent, "init", "--bare", remote.name)
    _run_git(target, "remote", "add", "origin", str(remote))
    worktree = root / "worktrees" / "sample" / "issue-001"
    (worktree / "README.md").write_text("# Sample\n\nMore detail.\n")
    _run_git(worktree, "add", "README.md")
    _run_git(worktree, "commit", "-m", "update readme")
    prepare_pull_request(root, "sample/issue-001", branch="feature/readme")
    original_run_command = pr_module._run_command
    calls: list[list[str]] = []

    def fake_run_command(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command and command[0] == "gh":
            return subprocess.CompletedProcess(command, 0, stdout="https://github.com/example/repo/pull/1\n", stderr="")
        return original_run_command(command, cwd=cwd)

    monkeypatch.setattr(pr_module, "_run_command", fake_run_command)

    published = publish_pull_request(root, "sample/issue-001", approved=True)

    assert published.url == "https://github.com/example/repo/pull/1"
    assert ["git", "-C", str(worktree), "push", "origin", "go-ship-it/issue-001:feature/readme"] in calls
    assert any(command[:3] == ["gh", "pr", "create"] for command in calls)
    run = yaml.safe_load(
        (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "run.yaml").read_text()
    )
    assert run["pull_request"]["published_url"] == "https://github.com/example/repo/pull/1"


def test_publish_pull_request_allows_repo_auto_publish_without_approval(tmp_path, monkeypatch):
    root = _started_issue_root(tmp_path)
    update_repo_config(root, "sample", updates={"pull_request": {"auto_publish": True}}, clears=set())
    target = root / "target"
    remote = tmp_path / "remote.git"
    _run_git(remote.parent, "init", "--bare", remote.name)
    _run_git(target, "remote", "add", "origin", str(remote))
    worktree = root / "worktrees" / "sample" / "issue-001"
    (worktree / "README.md").write_text("# Sample\n\nMore detail.\n")
    _run_git(worktree, "add", "README.md")
    _run_git(worktree, "commit", "-m", "update readme")
    prepare_pull_request(root, "sample/issue-001", branch="feature/readme")
    original_run_command = pr_module._run_command

    def fake_run_command(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if command and command[0] == "gh":
            return subprocess.CompletedProcess(command, 0, stdout="https://github.com/example/repo/pull/2\n", stderr="")
        return original_run_command(command, cwd=cwd)

    monkeypatch.setattr(pr_module, "_run_command", fake_run_command)

    published = publish_pull_request(root, "sample/issue-001")

    assert published.url == "https://github.com/example/repo/pull/2"


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
    start_issue(tmp_path, "sample/issue-001", claimed_by="test-thread")
    run_check(tmp_path, "sample/issue-001", check="test")
    write_handoff(tmp_path, "sample/issue-001")
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


def _run_git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *map(str, args)], cwd=cwd, capture_output=True, check=False, text=True)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout
