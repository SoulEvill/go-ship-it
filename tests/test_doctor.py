import json
from pathlib import Path
import subprocess

from go_ship_it.doctor import run_doctor
from go_ship_it.state import add_issue, register_repo, start_issue


def test_doctor_passes_minimal_valid_workspace(tmp_path):
    root = _root_with_repo(tmp_path)
    report = run_doctor(root)

    assert report.error_count == 0
    assert any(item.code == "layout.exists" for item in report.ok)


def test_doctor_errors_when_registered_repo_path_is_missing(tmp_path):
    register_repo(
        tmp_path,
        repo_id="missing",
        path=tmp_path / "does-not-exist",
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )

    report = run_doctor(tmp_path)

    assert report.error_count == 1
    assert report.errors[0].code == "repo.path_missing"


def test_doctor_warns_when_no_check_commands_are_configured(tmp_path):
    root = _root_with_repo(tmp_path, setup_command=None, test_command=None, lint_command=None)

    report = run_doctor(root)

    assert report.error_count == 0
    assert [item.code for item in report.warnings] == ["repo.no_checks_configured"]


def test_doctor_accepts_repo_with_only_test_command(tmp_path):
    root = _root_with_repo(tmp_path, setup_command=None, test_command="python -c 'print(\"test\")'", lint_command=None)

    report = run_doctor(root)

    assert report.error_count == 0
    assert not any(item.code == "repo.no_checks_configured" for item in report.warnings)
    assert any(item.code == "repo.test_command_configured" for item in report.ok)


def test_doctor_errors_for_duplicate_issue_ids(tmp_path):
    root = _root_with_repo(tmp_path)
    add_issue(root, repo_id="sample", title="One", problem="P", context="", acceptance_criteria=["A"])
    duplicate = root / "state" / "repos" / "sample" / "issues" / "archive" / "issue-001" / "issue.md"
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    duplicate.write_text(
        (root / "state" / "repos" / "sample" / "issues" / "todo" / "issue-001" / "issue.md").read_text()
    )

    report = run_doctor(root)

    assert any(item.code == "issue.duplicate_id" for item in report.errors)


def test_doctor_errors_when_execution_issue_has_no_run(tmp_path):
    root = _root_with_repo(tmp_path)
    add_issue(root, repo_id="sample", title="One", problem="P", context="", acceptance_criteria=["A"])
    start_issue(root, "sample/issue-001", claimed_by="test")
    run_file = root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "run.yaml"
    run_file.unlink()

    report = run_doctor(root)

    assert any(item.code == "run.missing_metadata" for item in report.errors)


def test_doctor_warns_for_preserved_worktree_without_issue_file(tmp_path):
    root = _root_with_repo(tmp_path)
    preserved = root / "worktrees" / "sample" / "issue-999"
    preserved.mkdir(parents=True)

    report = run_doctor(root)

    assert any(item.code == "worktree.preserved_without_issue" for item in report.warnings)


def test_doctor_checks_skill_files(tmp_path):
    root = _root_with_repo(tmp_path)
    skills = root / "skills" / "manage-issues"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("---\nname: manage-issues\n---\n\n## When To Use\n")

    report = run_doctor(root)

    assert any(item.code == "skill.exists" for item in report.ok)


def test_doctor_uses_bundled_package_root_for_package_checks(tmp_path):
    root = _root_with_repo(tmp_path)

    report = run_doctor(root)

    assert report.error_count == 0
    assert not any(item.code == "package.manifest_missing" for item in report.warnings)
    assert any(item.code == "package.manifest_ok" for item in report.ok)


def test_doctor_warns_when_plugin_package_files_are_missing(tmp_path, monkeypatch):
    root = _root_with_repo(tmp_path)
    monkeypatch.setattr("go_ship_it.doctor.package_root", lambda: root)

    report = run_doctor(root)

    assert report.error_count == 0
    assert any(item.code == "package.manifest_missing" for item in report.warnings)


def test_doctor_errors_when_plugin_manifest_is_invalid_json(tmp_path, monkeypatch):
    root = _root_with_repo(tmp_path)
    monkeypatch.setattr("go_ship_it.doctor.package_root", lambda: root)
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{not-json")

    report = run_doctor(root)

    assert any(item.code == "package.manifest_invalid" for item in report.errors)


def test_doctor_accepts_plugin_package_files(tmp_path, monkeypatch):
    root = _root_with_repo(tmp_path)
    _write_package_files(root)
    monkeypatch.setattr("go_ship_it.doctor.package_root", lambda: root)

    report = run_doctor(root)

    assert not any(item.code == "package.manifest_missing" for item in report.warnings)
    assert any(item.code == "package.manifest_ok" for item in report.ok)
    assert any(item.code == "package.bootstrap_ok" for item in report.ok)


def _write_package_files(root: Path) -> None:
    (root / "skills" / "using-go-ship-it").mkdir(parents=True)
    (root / "skills" / "using-go-ship-it" / "SKILL.md").write_text(
        "---\nname: using-go-ship-it\n---\n\n# Using GoShipit\n"
    )
    (root / "hooks").mkdir()
    (root / "hooks" / "hooks-cursor.json").write_text(
        '{"version":1,"hooks":{"sessionStart":[{"command":"./hooks/run-hook.cmd session-start"}]}}'
    )
    (root / "hooks" / "session-start").write_text("#!/usr/bin/env bash\n")
    (root / "hooks" / "run-hook.cmd").write_text("#!/usr/bin/env bash\n")
    for directory, extra in {
        ".claude-plugin": {},
        ".codex-plugin": {"skills": "./skills/"},
        ".cursor-plugin": {"skills": "./skills/", "hooks": "./hooks/hooks-cursor.json"},
    }.items():
        path = root / directory / "plugin.json"
        path.parent.mkdir()
        payload = {
            "name": "go-ship-it",
            "version": "0.1.0",
            "repository": "https://github.com/SoulEvill/go-ship-it",
            **extra,
        }
        path.write_text(json.dumps(payload))


def _root_with_repo(
    tmp_path: Path,
    *,
    setup_command: str | None = "python -c 'print(\"setup\")'",
    test_command: str | None = "python -c 'print(\"test\")'",
    lint_command: str | None = "python -c 'print(\"lint\")'",
) -> Path:
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=setup_command,
        test_command=test_command,
        lint_command=lint_command,
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
