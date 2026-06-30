from pathlib import Path
import subprocess

from go_ship_it import __version__
from go_ship_it.cli import build_parser, main
from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import add_issue, append_note, register_repo, run_check, start_issue


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

    export = parser.parse_args(["export-run", "issue-001", "--output", "docs/dogfood/issue-001-evidence.md"])
    assert export.command == "export-run"
    assert export.issue_id == "issue-001"
    assert export.output == "docs/dogfood/issue-001-evidence.md"


def test_parser_has_repo_config_commands():
    parser = build_parser()

    show = parser.parse_args(["show-repo", "parawave"])
    assert show.command == "show-repo"
    assert show.repo_id == "parawave"

    update = parser.parse_args(
        [
            "update-repo",
            "parawave",
            "--test-command",
            "env -u VIRTUAL_ENV uv run --extra dev pytest -q",
            "--clear-lint-command",
        ]
    )
    assert update.command == "update-repo"
    assert update.repo_id == "parawave"
    assert update.test_command == "env -u VIRTUAL_ENV uv run --extra dev pytest -q"
    assert update.clear_lint_command is True


def test_parser_has_navigation_commands():
    parser = build_parser()
    assert parser.parse_args(["list-issues"]).command == "list-issues"
    assert parser.parse_args(["list-issues", "--state", "execution", "--repo", "parawave"]).state == "execution"
    assert parser.parse_args(["show-issue", "issue-001"]).command == "show-issue"
    assert parser.parse_args(["show-run", "issue-001", "--commands"]).commands is True
    assert parser.parse_args(["status"]).command == "status"


def test_parser_has_doctor_command():
    parser = build_parser()

    args = parser.parse_args(["doctor"])

    assert args.command == "doctor"
    assert args.repo is None
    assert args.strict is False


def test_main_doctor_prints_summary(tmp_path, capsys):
    main(["--root", str(tmp_path), "init"])

    exit_code = main(["--root", str(tmp_path), "doctor"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "# GoShipit Doctor" in output
    assert "Summary:" in output


def test_main_show_repo_prints_yaml(tmp_path, capsys):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=Path("../sample"),
        default_branch="main",
        setup_command="uv sync",
        test_command="uv run pytest",
        lint_command=None,
    )

    exit_code = main(["--root", str(tmp_path), "show-repo", "sample"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == (
        "id: sample\n"
        "path: ../sample\n"
        "default_branch: main\n"
        "worktree_root: worktrees/sample\n"
        "setup_command: uv sync\n"
        "test_command: uv run pytest\n"
        "lint_command: null\n"
    )


def test_main_update_repo_changes_command(tmp_path):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=Path("../sample"),
        default_branch="main",
        setup_command="uv sync",
        test_command="uv run pytest",
        lint_command=None,
    )

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "update-repo",
            "sample",
            "--test-command",
            "env -u VIRTUAL_ENV uv run --extra dev pytest -q",
        ]
    )

    assert exit_code == 0
    text = (tmp_path / "state" / "repos" / "sample.yaml").read_text()
    assert "test_command: env -u VIRTUAL_ENV uv run --extra dev pytest -q" in text


def test_main_update_repo_rejects_command_and_clear_conflict(tmp_path, capsys):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=Path("../sample"),
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "update-repo",
            "sample",
            "--test-command",
            "pytest",
            "--clear-test-command",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "clear-test-command" in captured.err


def test_main_list_issues_prints_issue_summary(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "list-issues"])

    assert exit_code == 0
    assert "issue-001 [execution] sample - Change README" in capsys.readouterr().out


def test_main_list_issues_prints_no_matches(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "list-issues"])

    assert exit_code == 0
    assert capsys.readouterr().out == "No issues found.\n"


def test_main_show_issue_prints_body_and_metadata(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "show-issue", "issue-001"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "# issue-001" in out
    assert "Branch: go-ship-it/issue-001" in out
    assert "Worktree: worktrees/sample/issue-001" in out
    assert "Issue File: state/issues/execution/issue-001.md" in out
    assert "README needs another line." in out


def test_main_show_run_prints_summary_without_command_tails(tmp_path, capsys):
    root = _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")
    append_note(root, "issue-001", section="Investigation", note="Read files.", phase="investigate")
    run_check(root, "issue-001", check="test")

    exit_code = main(["--root", str(tmp_path), "show-run", "issue-001"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "# Run: issue-001" in out
    assert "- test exit 0: python -c 'print(\"ok\")'" in out
    assert "Read files." in out
    assert "Stdout tail:" not in out


def test_main_show_run_commands_prints_portable_tails(tmp_path, capsys):
    root = _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")
    run_check(root, "issue-001", check="test")
    capsys.readouterr()

    exit_code = main(["--root", str(tmp_path), "show-run", "issue-001", "--commands"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "## Command Records" in out
    assert "- CWD: `worktrees/sample/issue-001`" in out
    assert "Stdout tail:" in out
    assert "ok" in out
    assert str(tmp_path) not in out


def test_main_status_prints_workspace_summary(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "# GoShipit Status" in out
    assert "Repos: 1" in out
    assert "Execution: 1" in out
    assert "Managed Worktrees: 1" in out
    assert "- issue-001 sample Change README" in out
    assert "- sample/issue-001" in out


def test_main_export_run_relative_output_uses_root(tmp_path):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "export-run", "issue-001", "--output", "docs/dogfood/issue-001.md"])

    output = tmp_path / "docs" / "dogfood" / "issue-001.md"
    assert exit_code == 0
    assert output.exists()
    assert "# GoShipit Run Evidence: issue-001" in output.read_text()


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


def _started_issue_root(tmp_path: Path, *, test_command: str | None = None) -> Path:
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
