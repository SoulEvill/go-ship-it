from pathlib import Path
import subprocess

from go_ship_it.state import (
    add_issue,
    append_note,
    cleanup_issue,
    list_issues,
    register_repo,
    run_check,
    show_issue,
    show_run,
    start_issue,
)


def test_list_issues_returns_all_states_in_order(tmp_path):
    root = _root_with_repo(tmp_path)
    add_issue(root, repo_id="sample", title="Todo issue", problem="P", context="", acceptance_criteria=["A"])
    add_issue(root, repo_id="sample", title="Active issue", problem="P", context="", acceptance_criteria=["A"])
    add_issue(root, repo_id="sample", title="Archived issue", problem="P", context="", acceptance_criteria=["A"])
    start_issue(root, "issue-002", claimed_by="test")
    start_issue(root, "issue-003", claimed_by="test")
    cleanup_issue(root, "issue-003", destination="archive", note="Done.", remove_worktree=False)

    issues = list_issues(root)

    assert [(item.issue_id, item.status, item.title) for item in issues] == [
        ("issue-001", "todo", "Todo issue"),
        ("issue-002", "execution", "Active issue"),
        ("issue-003", "archive", "Archived issue"),
    ]


def test_list_issues_filters_state_and_repo(tmp_path):
    root = _root_with_repo(tmp_path)
    register_repo(
        root,
        repo_id="other",
        path=_create_git_repo(tmp_path / "other"),
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    add_issue(root, repo_id="sample", title="Sample", problem="P", context="", acceptance_criteria=["A"])
    add_issue(root, repo_id="other", title="Other", problem="P", context="", acceptance_criteria=["A"])
    start_issue(root, "issue-002", claimed_by="test")

    issues = list_issues(root, state="execution", repo_id="other")

    assert len(issues) == 1
    assert issues[0].issue_id == "issue-002"
    assert issues[0].repo == "other"


def test_show_issue_finds_archived_issue(tmp_path):
    root = _root_with_repo(tmp_path)
    add_issue(
        root,
        repo_id="sample",
        title="Archived issue",
        problem="Problem text",
        context="Context text",
        acceptance_criteria=["Done"],
    )
    start_issue(root, "issue-001", claimed_by="test")
    cleanup_issue(root, "issue-001", destination="archive", note="Done.", remove_worktree=False)

    detail = show_issue(root, "issue-001")

    assert detail.summary.issue_id == "issue-001"
    assert detail.summary.status == "archive"
    assert "Problem text" in detail.body


def test_show_run_returns_journal_and_command_summaries(tmp_path):
    root = _root_with_repo(tmp_path)
    add_issue(root, repo_id="sample", title="Run issue", problem="P", context="", acceptance_criteria=["A"])
    start_issue(root, "issue-001", claimed_by="test")
    append_note(root, "issue-001", section="Investigation", note="Read files.", phase="investigate")
    run_check(root, "issue-001", check="test")

    detail = show_run(root, "issue-001")

    assert detail.issue_id == "issue-001"
    assert "Read files." in detail.journal
    assert len(detail.commands) == 1
    assert detail.commands[0]["check"] == "test"


def _root_with_repo(tmp_path: Path) -> Path:
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
