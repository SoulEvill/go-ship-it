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
    set_phase,
    start_issue,
    write_handoff,
)
from go_ship_it.verify import verify_run


def test_verify_run_warns_when_export_precedes_cleanup(tmp_path):
    root = _started_issue_root(tmp_path)
    _write_required_notes(root, "issue-001")
    run_check(root, "issue-001", check="test")
    export_run(root, "issue-001", output=tmp_path / "docs" / "dogfood" / "before-cleanup.md")
    cleanup_issue(root, "issue-001", destination="archive", note="Done.", remove_worktree=False)

    report = verify_run(root, "issue-001")

    assert not report.errors
    assert any(item.code == "run.export_stale" for item in report.warnings)
    assert any(item.code == "worktree.preserved_after_archive" for item in report.warnings)


def test_verify_run_warns_when_legacy_export_lacks_metadata_after_cleanup(tmp_path):
    root = _started_issue_root(tmp_path)
    _write_required_notes(root, "issue-001")
    run_check(root, "issue-001", check="test")
    cleanup_issue(root, "issue-001", destination="archive", note="Done.", remove_worktree=False)
    legacy_export = root / "docs" / "dogfood" / "legacy-export.md"
    legacy_export.parent.mkdir(parents=True)
    legacy_export.write_text(
        "# GoShipit Run Evidence: issue-001\n\n"
        "Source: `state/issues/execution/issue-001.md`\n\n"
        "```yaml\nphase: test\n```\n"
    )

    report = verify_run(root, "issue-001")

    assert not report.errors
    assert any(item.code == "run.export_stale" for item in report.warnings)


def test_verify_run_accepts_export_after_cleanup(tmp_path):
    root = _started_issue_root(tmp_path)
    _write_required_notes(root, "issue-001")
    run_check(root, "issue-001", check="test")
    cleanup_issue(root, "issue-001", destination="archive", note="Done.", remove_worktree=False)
    export_run(root, "issue-001", output=tmp_path / "docs" / "dogfood" / "after-cleanup.md")

    report = verify_run(root, "issue-001")

    assert not report.errors
    assert not any(item.code == "run.export_stale" for item in report.warnings)
    assert any(item.code == "run.export_fresh" for item in report.ok)


def test_verify_run_errors_on_failed_command(tmp_path):
    root = _started_issue_root(tmp_path, test_command="python -c 'import sys; sys.exit(7)'")
    _write_required_notes(root, "issue-001")
    with pytest.raises(CheckFailedError):
        run_check(root, "issue-001", check="test")

    report = verify_run(root, "issue-001")

    assert any(item.code == "command.failed" for item in report.errors)


def test_verify_run_warns_when_acceptance_criteria_lack_evidence(tmp_path):
    root = _started_issue_root(tmp_path)
    _write_required_notes(root, "issue-001")
    run_check(root, "issue-001", check="test")

    report = verify_run(root, "issue-001")

    assert any(item.code == "acceptance.criteria_missing_evidence" for item in report.warnings)


def test_verify_run_accepts_acceptance_criteria_with_evidence(tmp_path):
    root = _started_issue_root(tmp_path)
    _write_required_notes(root, "issue-001")
    append_note(
        root,
        "issue-001",
        section="Review",
        phase="test",
        note="Acceptance evidence: README changes. Verified by the test check.",
    )
    run_check(root, "issue-001", check="test")

    report = verify_run(root, "issue-001")

    assert not any(item.code == "acceptance.criteria_missing_evidence" for item in report.warnings)
    assert any(item.code == "acceptance.criteria_covered" for item in report.ok)


def test_verify_run_warns_when_active_run_handoff_is_missing(tmp_path):
    root = _started_issue_root(tmp_path)
    _write_required_notes(root, "issue-001")
    run_check(root, "issue-001", check="test")

    report = verify_run(root, "issue-001")

    assert any(item.code == "handoff.missing" for item in report.warnings)


def test_verify_run_accepts_active_run_handoff(tmp_path):
    root = _started_issue_root(tmp_path)
    _write_required_notes(root, "issue-001")
    run_check(root, "issue-001", check="test")
    write_handoff(root, "issue-001")

    report = verify_run(root, "issue-001")

    assert not any(item.code == "handoff.missing" for item in report.warnings)
    assert any(item.code == "handoff.present" for item in report.ok)


def _write_required_notes(root: Path, issue_id: str) -> None:
    set_phase(root, issue_id, "investigate", note="Investigating.")
    append_note(root, issue_id, section="Investigation", phase="investigate", note="Read context.")
    set_phase(root, issue_id, "propose", note="Proposal ready.")
    append_note(root, issue_id, section="Proposal", phase="propose", note="Use small fix.")
    set_phase(root, issue_id, "implement", note="Implementation ready.")
    append_note(root, issue_id, section="Implementation", phase="implement", note="Changed files.")
    set_phase(root, issue_id, "test", note="Testing.")
    append_note(root, issue_id, section="Review", phase="test", note="Ready.")


def _started_issue_root(tmp_path: Path, *, test_command: str = "python -c 'print(\"ok\")'") -> Path:
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
