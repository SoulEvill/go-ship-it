from pathlib import Path
import json
import subprocess

import yaml

from go_ship_it import __version__
from go_ship_it.cli import build_parser, main
from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import add_issue, append_note, register_repo, run_check, set_phase, start_issue


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
    assert "Normal path:" in captured.out
    assert "Advanced/support:" in captured.out


def test_parser_has_package_root_command():
    parser = build_parser()
    args = parser.parse_args(["package-root"])

    assert args.command == "package-root"


def test_main_package_root_prints_existing_agent_package(capsys):
    exit_code = main(["package-root"])
    captured = capsys.readouterr()

    package_root = Path(captured.out.strip())
    assert exit_code == 0
    assert (package_root / "skills" / "using-go-ship-it" / "SKILL.md").exists()
    assert (package_root / ".claude-plugin" / "plugin.json").exists()
    assert (package_root / ".cursor-plugin" / "plugin.json").exists()
    assert (package_root / ".codex-plugin" / "plugin.json").exists()


def test_main_init_creates_state_layout(tmp_path):
    exit_code = main(["--root", str(tmp_path), "init"])

    assert exit_code == 0
    assert (tmp_path / "state" / "repos").is_dir()
    assert not (tmp_path / "state" / "issues").exists()


def test_main_init_can_register_first_repo(tmp_path):
    target = _create_git_repo(tmp_path / "target")

    exit_code = main(
        [
            "--root",
            str(tmp_path / "control"),
            "init",
            "--repo-id",
            "sample",
            "--repo-path",
            str(target),
            "--test-command",
            "python -c 'print(\"ok\")'",
        ]
    )

    repo_file = tmp_path / "control" / "state" / "repos" / "sample" / "repo.yaml"
    assert exit_code == 0
    assert repo_file.exists()
    text = repo_file.read_text()
    assert "id: sample\n" in text
    assert f"path: {target}\n" in text
    assert "test_command: python -c 'print(\"ok\")'\n" in text


def test_main_init_rejects_partial_repo_registration(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "init", "--repo-id", "sample"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "--repo-id and --repo-path must be provided together" in captured.err


def test_register_repo_cli_preserves_relative_paths(tmp_path):
    exit_code = main(["--root", str(tmp_path), "register-repo", "sample", "../sample-target"])

    assert exit_code == 0
    assert "path: ../sample-target\n" in (
        tmp_path / "state" / "repos" / "sample" / "repo.yaml"
    ).read_text()


def test_parser_has_evidence_commands():
    parser = build_parser()

    append = parser.parse_args(["append-note", "sample/issue-001", "--section", "Investigation", "--note", "Read README"])
    assert append.command == "append-note"
    assert append.issue_id == "sample/issue-001"
    assert append.section == "Investigation"
    assert append.note == "Read README"

    phase = parser.parse_args(["set-phase", "sample/issue-001", "propose", "--note", "Ready to propose"])
    assert phase.command == "set-phase"
    assert phase.issue_id == "sample/issue-001"
    assert phase.phase == "propose"
    assert phase.note == "Ready to propose"

    check = parser.parse_args(["run-check", "sample/issue-001", "--check", "test"])
    assert check.command == "run-check"
    assert check.issue_id == "sample/issue-001"
    assert check.check == "test"

    export = parser.parse_args(["export-run", "sample/issue-001", "--output", "docs/dogfood/sample-issue-001-evidence.md"])
    assert export.command == "export-run"
    assert export.issue_id == "sample/issue-001"
    assert export.output == "docs/dogfood/sample-issue-001-evidence.md"


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
    assert parser.parse_args(["show-issue", "sample/issue-001"]).command == "show-issue"
    assert parser.parse_args(["show-issue", "--current"]).current is True
    assert parser.parse_args(["show-run", "sample/issue-001", "--commands"]).commands is True
    assert parser.parse_args(["show-run", "--current", "--commands"]).current is True
    assert parser.parse_args(["show-run", "sample/issue-001", "--trace"]).trace is True
    assert parser.parse_args(["show-run", "sample/issue-001", "--handoff"]).handoff is True
    assert parser.parse_args(["handoff", "sample/issue-001"]).command == "handoff"
    assert parser.parse_args(["handoff", "sample/issue-001", "--write"]).write is True
    assert parser.parse_args(["handoff", "--current", "--write"]).current is True
    status = parser.parse_args(["status", "--json"])
    assert status.command == "status"
    assert status.json is True


def test_parser_has_verify_run_command():
    parser = build_parser()

    args = parser.parse_args(["verify-run", "sample/issue-001", "--strict", "--json"])

    assert args.command == "verify-run"
    assert args.issue_id == "sample/issue-001"
    assert args.strict is True
    assert args.json is True


def test_parser_has_doctor_command():
    parser = build_parser()

    args = parser.parse_args(["doctor", "--json"])

    assert args.command == "doctor"
    assert args.repo is None
    assert args.strict is False
    assert args.json is True


def test_main_doctor_prints_summary(tmp_path, capsys):
    main(["--root", str(tmp_path), "init"])

    exit_code = main(["--root", str(tmp_path), "doctor"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "# GoShipit Doctor" in output
    assert "Summary:" in output


def test_main_doctor_json_prints_structured_summary(tmp_path, capsys):
    main(["--root", str(tmp_path), "init"])
    capsys.readouterr()

    exit_code = main(["--root", str(tmp_path), "doctor", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["summary"]["errors"] == 0
    assert "findings" in payload
    assert {"errors", "warnings", "ok"} <= set(payload["findings"])


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
        "context_file: state/repos/sample/context.md\n"
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
    text = (tmp_path / "state" / "repos" / "sample" / "repo.yaml").read_text()
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
    assert "sample/issue-001 [execution] - Change README" in capsys.readouterr().out


def test_main_list_issues_prints_no_matches(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "list-issues"])

    assert exit_code == 0
    assert capsys.readouterr().out == "No issues found.\n"


def test_main_show_issue_prints_body_and_metadata(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "show-issue", "sample/issue-001"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "# sample/issue-001" in out
    assert "Branch: go-ship-it/issue-001" in out
    assert "Worktree: worktrees/sample/issue-001" in out
    assert "Issue File: state/repos/sample/issues/execution/issue-001/issue.md" in out
    assert "README needs another line." in out


def test_main_show_run_prints_summary_without_command_tails(tmp_path, capsys):
    root = _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")
    append_note(root, "sample/issue-001", section="Investigation", note="Read files.", phase="investigate")
    run_check(root, "sample/issue-001", check="test")

    exit_code = main(["--root", str(tmp_path), "show-run", "sample/issue-001"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "# Run: sample/issue-001" in out
    assert "- test exit 0: python -c 'print(\"ok\")'" in out
    assert "Read files." in out
    assert "Stdout tail:" not in out


def test_main_show_run_commands_prints_portable_tails(tmp_path, capsys):
    root = _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")
    run_check(root, "sample/issue-001", check="test")
    capsys.readouterr()

    exit_code = main(["--root", str(tmp_path), "show-run", "sample/issue-001", "--commands"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "## Command Records" in out
    assert "- CWD: `worktrees/sample/issue-001`" in out
    assert "Stdout tail:" in out
    assert "ok" in out
    assert str(tmp_path) not in out


def test_main_show_run_trace_prints_timeline(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "show-run", "sample/issue-001", "--trace"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# Trace: sample/issue-001" in output
    assert "issue.created" in output
    assert "run.started" in output


def test_main_show_run_handoff_prints_resume_context(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "show-run", "sample/issue-001", "--handoff"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# GoShipit Handoff: sample/issue-001" in output
    assert "Claimed By: `test-thread`" in output
    assert "Claim ID: `claim-issue-001-" in output
    assert "go-ship-it verify-run sample/issue-001" in output


def test_main_handoff_write_creates_resume_file(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "handoff", "sample/issue-001", "--write"])

    assert exit_code == 0
    output_path = tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "handoff.md"
    assert capsys.readouterr().out == f"{output_path}\n"
    assert "# GoShipit Handoff: sample/issue-001" in output_path.read_text()


def test_main_handoff_output_writes_custom_resume_file(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "handoff",
            "sample/issue-001",
            "--output",
            "handoffs/issue-001.md",
        ]
    )

    output_path = tmp_path / "handoffs" / "issue-001.md"
    assert exit_code == 0
    assert capsys.readouterr().out == f"{output_path}\n"
    assert output_path.exists()


def test_main_current_handoff_uses_worktree_context(tmp_path, monkeypatch, capsys):
    root = _started_issue_root(tmp_path)
    worktree = root / "worktrees" / "sample" / "issue-001"
    monkeypatch.chdir(worktree)

    exit_code = main(["handoff", "--current", "--write"])

    output_path = root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "handoff.md"
    assert exit_code == 0
    assert capsys.readouterr().out == f"{output_path}\n"
    assert "# GoShipit Handoff: sample/issue-001" in output_path.read_text()


def test_main_handoff_without_issue_auto_uses_worktree_context(tmp_path, monkeypatch, capsys):
    root = _started_issue_root(tmp_path)
    monkeypatch.chdir(root / "worktrees" / "sample" / "issue-001")

    exit_code = main(["handoff", "--write"])

    output_path = root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "handoff.md"
    assert exit_code == 0
    assert capsys.readouterr().out == f"{output_path}\n"


def test_main_show_run_without_issue_auto_uses_worktree_context(tmp_path, monkeypatch, capsys):
    root = _started_issue_root(tmp_path)
    monkeypatch.chdir(root / "worktrees" / "sample" / "issue-001")

    exit_code = main(["show-run"])

    assert exit_code == 0
    assert "# Run: sample/issue-001" in capsys.readouterr().out


def test_main_current_show_run_rejects_context_claim_mismatch(tmp_path, monkeypatch, capsys):
    root = _started_issue_root(tmp_path)
    worktree = root / "worktrees" / "sample" / "issue-001"
    context_file = worktree / ".go-ship-it" / "context.yaml"
    context = yaml.safe_load(context_file.read_text())
    context["claim_id"] = "claim-issue-001-wrong"
    context_file.write_text(yaml.safe_dump(context, sort_keys=False))
    monkeypatch.chdir(worktree)

    exit_code = main(["show-run", "--current"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "claim mismatch" in captured.err


def test_main_verify_run_prints_report(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "verify-run", "sample/issue-001"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# GoShipit Run Verification: sample/issue-001" in output
    assert "Summary:" in output


def test_main_verify_run_json_prints_structured_findings(tmp_path, capsys):
    _started_issue_root(tmp_path)
    capsys.readouterr()

    exit_code = main(["--root", str(tmp_path), "verify-run", "sample/issue-001", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["issue_id"] == "sample/issue-001"
    assert payload["summary"]["errors"] == 0
    assert "findings" in payload
    assert any(item["code"] == "run.exists" for item in payload["findings"]["ok"])


def test_main_status_prints_workspace_summary(tmp_path, capsys):
    _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")

    exit_code = main(["--root", str(tmp_path), "status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "# GoShipit Status" in out
    assert f"Control Root: {tmp_path.resolve()}" in out
    assert "Package Root:" in out
    assert "Current Git Branch:" in out
    assert "Repos: 1" in out
    assert "Execution: 1" in out
    assert "Managed Worktrees: 1" in out
    assert "- sample/issue-001 Change README" in out
    assert "Phase: investigate" in out
    assert "Claimed By: test-thread" in out
    assert "Claim ID: claim-issue-001-" in out
    assert "Worktree: worktrees/sample/issue-001" in out
    assert "go-ship-it show-run sample/issue-001" in out
    assert "go-ship-it show-run sample/issue-001 --trace" in out
    assert "go-ship-it show-run sample/issue-001 --handoff" in out
    assert "go-ship-it append-note sample/issue-001 --section \"Investigation\"" in out
    assert "go-ship-it set-phase sample/issue-001 propose" in out
    assert "go-ship-it run-check sample/issue-001 --check test" in out
    assert "go-ship-it verify-run sample/issue-001 --strict" in out
    assert "go-ship-it cleanup-issue sample/issue-001 --destination archive --note \"<note>\" --remove-worktree" in out
    assert "- sample/issue-001" in out


def test_main_status_json_prints_structured_workspace(tmp_path, capsys):
    _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")
    capsys.readouterr()

    exit_code = main(["--root", str(tmp_path), "status", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["summary"]["repos"] == 1
    assert payload["summary"]["execution"] == 1
    assert payload["active"][0]["issue_id"] == "issue-001"
    assert payload["active"][0]["issue_ref"] == "sample/issue-001"
    assert payload["active"][0]["phase"] == "investigate"
    assert "go-ship-it set-phase sample/issue-001 propose --note \"<investigation summary>\"" in payload["active"][0]["next_commands"]


def test_main_status_guides_proposal_phase_to_implementation(tmp_path, capsys):
    root = _started_issue_root(tmp_path)
    set_phase(root, "sample/issue-001", "propose", note="Ready to propose.")

    exit_code = main(["--root", str(root), "status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Phase: propose" in out
    assert "go-ship-it append-note sample/issue-001 --section \"Proposal\"" in out
    assert "go-ship-it set-phase sample/issue-001 implement --note \"<proposal accepted>\"" in out


def test_main_status_guides_implementation_phase_to_test(tmp_path, capsys):
    root = _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")
    set_phase(root, "sample/issue-001", "implement", note="Implementation started.")

    exit_code = main(["--root", str(root), "status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Phase: implement" in out
    assert "go-ship-it append-note sample/issue-001 --section \"Implementation\"" in out
    assert "go-ship-it set-phase sample/issue-001 test --note \"<ready for checks>\"" in out
    assert "go-ship-it run-check sample/issue-001 --check test" in out


def test_main_status_guides_test_phase_to_readiness_sequence(tmp_path, capsys):
    root = _started_issue_root(tmp_path, test_command="python -c 'print(\"ok\")'")
    set_phase(root, "sample/issue-001", "test", note="Ready for checks.")

    exit_code = main(["--root", str(root), "status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Phase: test" in out
    assert "go-ship-it run-check sample/issue-001 --check test" in out
    assert "go-ship-it handoff sample/issue-001 --write" in out
    assert "go-ship-it export-run sample/issue-001 --output docs/dogfood/sample-issue-001-evidence.md" in out
    assert "go-ship-it verify-run sample/issue-001 --strict" in out
    assert "go-ship-it cleanup-issue sample/issue-001 --destination archive --note \"<note>\" --remove-worktree" in out


def test_main_status_guides_empty_control_root(tmp_path, capsys):
    main(["--root", str(tmp_path), "init"])
    capsys.readouterr()

    exit_code = main(["--root", str(tmp_path), "status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Repos: 0" in out
    assert "## Next Steps" in out
    assert "go-ship-it register-repo <repo-id> <path>" in out
    assert "go-ship-it add-issue --repo <repo-id>" in out


def test_main_status_lists_todo_issues_with_start_hint(tmp_path, capsys):
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

    exit_code = main(["--root", str(tmp_path), "status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Todo: 1" in out
    assert "## Todo Issues" in out
    assert "- sample/issue-001 Change README" in out
    assert "go-ship-it start-issue sample/issue-001" in out


def test_main_status_from_worktree_uses_current_control_root(tmp_path, monkeypatch, capsys):
    root = _started_issue_root(tmp_path)
    monkeypatch.chdir(root / "worktrees" / "sample" / "issue-001")

    exit_code = main(["status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert f"Control Root: {root.resolve()}" in out
    assert "Current Issue: sample/issue-001" in out
    assert "Current Worktree: worktrees/sample/issue-001" in out
    assert "Current Run Branch: go-ship-it/issue-001" in out
    assert "- sample/issue-001 Change README" in out


def test_main_status_omits_unconfigured_check_hint(tmp_path, capsys):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "status"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "go-ship-it show-run sample/issue-001" in out
    assert "go-ship-it show-run sample/issue-001 --trace" in out
    assert "go-ship-it show-run sample/issue-001 --handoff" in out
    assert "go-ship-it run-check sample/issue-001 --check test" not in out
    assert "go-ship-it verify-run sample/issue-001 --strict" in out
    assert "go-ship-it cleanup-issue sample/issue-001 --destination archive --note \"<note>\" --remove-worktree" in out


def test_main_status_rejects_uninitialized_root(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "status"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "not an initialized GoShipit control repo" in captured.err
    assert "go-ship-it init" in captured.err
    assert "--root" in captured.err


def test_main_export_run_relative_output_uses_root(tmp_path):
    _started_issue_root(tmp_path)

    exit_code = main(["--root", str(tmp_path), "export-run", "sample/issue-001", "--output", "docs/dogfood/issue-001.md"])

    output = tmp_path / "docs" / "dogfood" / "issue-001.md"
    assert exit_code == 0
    assert output.exists()
    assert "# GoShipit Run Evidence: sample/issue-001" in output.read_text()


def test_main_append_note_records_note_entry(tmp_path):
    _started_issue_root(tmp_path)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "append-note",
            "sample/issue-001",
            "--section",
            "Investigation",
            "--note",
            "Read README",
            "--phase",
            "investigate",
        ]
    )

    assert exit_code == 0
    notes = (
        tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "notes.md"
    ).read_text()
    assert "## Investigation" in notes
    assert "Read README" in notes
    assert "Phase: investigate" in notes


def test_main_append_note_current_records_note_entry(tmp_path, monkeypatch):
    root = _started_issue_root(tmp_path)
    monkeypatch.chdir(root / "worktrees" / "sample" / "issue-001")

    exit_code = main(
        [
            "append-note",
            "--current",
            "--section",
            "Investigation",
            "--note",
            "Read README from locked session.",
            "--phase",
            "investigate",
        ]
    )

    notes = root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "notes.md"
    assert exit_code == 0
    assert "Read README from locked session." in notes.read_text()


def test_main_set_phase_updates_active_issue(tmp_path):
    _started_issue_root(tmp_path)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "set-phase",
            "sample/issue-001",
            "propose",
            "--note",
            "Ready to propose",
        ]
    )

    assert exit_code == 0
    metadata, _body = parse_frontmatter(
        (tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "issue.md").read_text()
    )
    assert metadata["phase"] == "propose"
    notes = (
        tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "notes.md"
    ).read_text()
    assert "Ready to propose" in notes


def test_main_set_phase_current_updates_active_issue(tmp_path, monkeypatch):
    root = _started_issue_root(tmp_path)
    monkeypatch.chdir(root / "worktrees" / "sample" / "issue-001")

    exit_code = main(["set-phase", "--current", "propose", "--note", "Ready to propose"])

    assert exit_code == 0
    metadata, _body = parse_frontmatter(
        (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "issue.md").read_text()
    )
    assert metadata["phase"] == "propose"


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
