from pathlib import Path
import subprocess

from go_ship_it.state import (
    add_issue,
    append_note,
    cleanup_issue,
    export_run,
    register_repo,
    run_check,
    run_timeline,
    set_phase,
    start_issue,
)


def test_run_timeline_orders_generated_issue_note_command_cleanup_and_export_events(tmp_path):
    root = _started_issue_root(tmp_path)
    set_phase(root, "sample/issue-001", "propose", note="Ready to propose.")
    append_note(root, "sample/issue-001", section="Proposal", phase="propose", note="Use the small fix.")
    run_check(root, "sample/issue-001", check="test")
    cleanup_issue(root, "sample/issue-001", destination="archive", note="Done.", remove_worktree=False)
    export_run(root, "sample/issue-001", output=tmp_path / "docs" / "dogfood" / "issue-001.md")

    events = run_timeline(root, "sample/issue-001")
    kinds = [event.kind for event in events]

    assert "issue.created" in kinds
    assert "run.started" in kinds
    assert "phase.changed" in kinds
    assert "note.appended" in kinds
    assert "check.test" in kinds
    assert "run.cleanup" in kinds
    assert "export.written" in kinds
    assert events == sorted(events, key=lambda event: event.timestamp)


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
