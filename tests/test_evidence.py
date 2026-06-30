from pathlib import Path
import subprocess

import pytest
import yaml

from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import append_note, add_issue, register_repo, set_phase, start_issue


def test_append_note_creates_journal_for_active_issue(tmp_path):
    root = _started_issue_root(tmp_path)

    journal = append_note(root, "issue-001", section="Investigation", note="Read README.")

    assert journal == root / "state" / "runs" / "issue-001" / "journal.md"
    text = journal.read_text()
    assert "## Investigation" in text
    assert "Read README." in text
    assert "Timestamp:" in text


def test_set_phase_updates_issue_run_and_journal(tmp_path):
    root = _started_issue_root(tmp_path)

    issue_file = set_phase(root, "issue-001", "propose", note="Investigation complete.")

    metadata, _body = parse_frontmatter(issue_file.read_text())
    assert metadata["phase"] == "propose"
    assert isinstance(metadata["last_activity_at"], str)

    run = yaml.safe_load((root / "state" / "runs" / "issue-001" / "run.yaml").read_text())
    assert run["phase"] == "propose"
    assert isinstance(run["last_activity_at"], str)

    journal = (root / "state" / "runs" / "issue-001" / "journal.md").read_text()
    assert "## Phase: propose" in journal
    assert "Investigation complete." in journal


def test_set_phase_rejects_invalid_phase(tmp_path):
    root = _started_issue_root(tmp_path)

    with pytest.raises(ValueError, match="phase"):
        set_phase(root, "issue-001", "banana", note="Nope.")


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
