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


def test_doctor_warns_for_missing_optional_commands(tmp_path):
    root = _root_with_repo(tmp_path, setup_command=None, test_command=None, lint_command=None)

    report = run_doctor(root)

    assert report.error_count == 0
    assert {item.code for item in report.warnings} >= {
        "repo.setup_command_missing",
        "repo.test_command_missing",
        "repo.lint_command_missing",
    }


def test_doctor_errors_for_duplicate_issue_ids(tmp_path):
    root = _root_with_repo(tmp_path)
    add_issue(root, repo_id="sample", title="One", problem="P", context="", acceptance_criteria=["A"])
    duplicate = root / "state" / "issues" / "archive" / "issue-001.md"
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    duplicate.write_text((root / "state" / "issues" / "todo" / "issue-001.md").read_text())

    report = run_doctor(root)

    assert any(item.code == "issue.duplicate_id" for item in report.errors)


def test_doctor_errors_when_execution_issue_has_no_run(tmp_path):
    root = _root_with_repo(tmp_path)
    add_issue(root, repo_id="sample", title="One", problem="P", context="", acceptance_criteria=["A"])
    start_issue(root, "issue-001", claimed_by="test")
    run_file = root / "state" / "runs" / "issue-001" / "run.yaml"
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
    skills = root / "skills" / "add-issue"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("---\nname: add-issue\n---\n\n## When To Use\n")

    report = run_doctor(root)

    assert any(item.code == "skill.exists" for item in report.ok)


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
