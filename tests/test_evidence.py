from pathlib import Path
import subprocess

import pytest
import yaml

from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import append_note, add_issue, register_repo, set_phase, start_issue


def test_append_note_creates_notes_for_active_issue(tmp_path):
    root = _started_issue_root(tmp_path)

    notes = append_note(root, "sample/issue-001", section="Investigation", note="Read README.")

    assert notes == root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "notes.md"
    text = notes.read_text()
    assert "## Investigation" in text
    assert "Read README." in text
    assert "Timestamp:" in text


def test_set_phase_updates_issue_run_and_notes(tmp_path):
    root = _started_issue_root(tmp_path)

    issue_file = set_phase(root, "sample/issue-001", "propose", note="Investigation complete.")

    metadata, _body = parse_frontmatter(issue_file.read_text())
    assert metadata["phase"] == "propose"
    assert isinstance(metadata["last_activity_at"], str)

    run = yaml.safe_load(
        (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "run.yaml").read_text()
    )
    assert run["phase"] == "propose"
    assert isinstance(run["last_activity_at"], str)

    notes = (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "notes.md").read_text()
    assert "## Phase: propose" in notes
    assert "Investigation complete." in notes


def test_set_phase_rejects_invalid_phase(tmp_path):
    root = _started_issue_root(tmp_path)

    with pytest.raises(ValueError, match="phase"):
        set_phase(root, "sample/issue-001", "banana", note="Nope.")


def test_phase_enum_accepts_all_lifecycle_phases(tmp_path):
    root = _started_issue_root(tmp_path)
    from go_ship_it.state import PHASES

    assert PHASES == (
        "setup",
        "investigate",
        "propose",
        "implement",
        "review",
        "prepare-pr",
        "publish",
        "archived",
    )
    for phase in ("review", "prepare-pr", "publish"):
        issue_file = set_phase(root, "sample/issue-001", phase, note=f"Entering {phase}.")
        assert issue_file.exists()


def test_phase_enum_rejects_retired_phase_names(tmp_path):
    root = _started_issue_root(tmp_path)
    for retired in ("test", "cleanup"):
        with pytest.raises(ValueError, match="phase must be one of"):
            set_phase(root, "sample/issue-001", retired, note="Nope.")


def test_entering_implement_records_default_tdd_inner_loop(tmp_path):
    root = _started_issue_root(tmp_path)
    set_phase(root, "sample/issue-001", "implement", note="Building.")
    run = yaml.safe_load(_run_file(root).read_text())
    assert run["inner_loop"] == "tdd"


def test_entering_implement_with_none_loop_requires_reason(tmp_path):
    root = _started_issue_root(tmp_path)
    with pytest.raises(ValueError, match="requires --inner-loop-reason"):
        set_phase(root, "sample/issue-001", "implement", note="Building.", inner_loop="none")
    set_phase(
        root,
        "sample/issue-001",
        "implement",
        note="Docs only.",
        inner_loop="none",
        inner_loop_reason="Docs-only change; no executable behavior.",
    )
    run = yaml.safe_load(_run_file(root).read_text())
    assert run["inner_loop"] == "none"
    assert run["inner_loop_reason"] == "Docs-only change; no executable behavior."


def test_entering_review_records_default_self_pipeline(tmp_path):
    root = _started_issue_root(tmp_path)
    set_phase(root, "sample/issue-001", "review", note="Reviewing.")
    run = yaml.safe_load(_run_file(root).read_text())
    assert run["review_pipeline"] == "self"


def test_review_pipeline_accepts_plugin_form_and_rejects_junk(tmp_path):
    root = _started_issue_root(tmp_path)
    set_phase(root, "sample/issue-001", "review", note="R.", review_pipeline="plugin:code-review")
    run = yaml.safe_load(_run_file(root).read_text())
    assert run["review_pipeline"] == "plugin:code-review"
    with pytest.raises(ValueError, match="review_pipeline"):
        set_phase(root, "sample/issue-001", "review", note="R.", review_pipeline="vibes")
    with pytest.raises(ValueError, match="review_pipeline"):
        set_phase(root, "sample/issue-001", "review", note="R.", review_pipeline="plugin:")


def test_axis_flags_rejected_outside_their_phase(tmp_path):
    root = _started_issue_root(tmp_path)
    with pytest.raises(ValueError, match="inner-loop"):
        set_phase(root, "sample/issue-001", "propose", note="P.", inner_loop="tdd")
    with pytest.raises(ValueError, match="review-pipeline"):
        set_phase(root, "sample/issue-001", "implement", note="I.", review_pipeline="self")


def _run_file(root: Path) -> Path:
    return root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "run.yaml"


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
