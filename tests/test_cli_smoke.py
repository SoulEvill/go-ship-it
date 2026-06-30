from pathlib import Path
import subprocess

from go_ship_it import __version__
from go_ship_it.cli import build_parser, main
from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import add_issue, register_repo, start_issue


def test_version_is_defined():
    assert __version__ == "0.1.0"


def test_parser_has_init_command():
    parser = build_parser()
    args = parser.parse_args(["init"])
    assert args.command == "init"


def test_main_help_exits_cleanly(capsys):
    exit_code = main(["--help"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "GoShipit" in captured.out


def test_main_init_creates_state_layout(tmp_path):
    exit_code = main(["--root", str(tmp_path), "init"])

    assert exit_code == 0
    assert (tmp_path / "state" / "repos").is_dir()
    assert (tmp_path / "state" / "issues" / "todo").is_dir()


def test_register_repo_cli_preserves_relative_paths(tmp_path):
    exit_code = main(["--root", str(tmp_path), "register-repo", "sample", "../sample-target"])

    assert exit_code == 0
    assert "path: ../sample-target\n" in (tmp_path / "state" / "repos" / "sample.yaml").read_text()


def test_parser_has_evidence_commands():
    parser = build_parser()

    append = parser.parse_args(["append-note", "issue-001", "--section", "Investigation", "--note", "Read README"])
    assert append.command == "append-note"
    assert append.issue_id == "issue-001"
    assert append.section == "Investigation"
    assert append.note == "Read README"

    phase = parser.parse_args(["set-phase", "issue-001", "propose", "--note", "Ready to propose"])
    assert phase.command == "set-phase"
    assert phase.issue_id == "issue-001"
    assert phase.phase == "propose"
    assert phase.note == "Ready to propose"

    check = parser.parse_args(["run-check", "issue-001", "--check", "test"])
    assert check.command == "run-check"
    assert check.issue_id == "issue-001"
    assert check.check == "test"


def test_main_append_note_records_journal_entry(tmp_path):
    _started_issue_root(tmp_path)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "append-note",
            "issue-001",
            "--section",
            "Investigation",
            "--note",
            "Read README",
            "--phase",
            "investigate",
        ]
    )

    assert exit_code == 0
    journal = (tmp_path / "state" / "runs" / "issue-001" / "journal.md").read_text()
    assert "## Investigation" in journal
    assert "Read README" in journal
    assert "Phase: investigate" in journal


def test_main_set_phase_updates_active_issue(tmp_path):
    _started_issue_root(tmp_path)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "set-phase",
            "issue-001",
            "propose",
            "--note",
            "Ready to propose",
        ]
    )

    assert exit_code == 0
    metadata, _body = parse_frontmatter(
        (tmp_path / "state" / "issues" / "execution" / "issue-001.md").read_text()
    )
    assert metadata["phase"] == "propose"
    journal = (tmp_path / "state" / "runs" / "issue-001" / "journal.md").read_text()
    assert "Ready to propose" in journal


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
